"""Independent feature proof: migration -> API -> constraints -> race -> restore."""
from pathlib import Path
from datetime import datetime,timedelta,timezone
from uuid import uuid4,UUID
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import importlib.util,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import text,inspect
from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed,headers
from labs.shared.history_lab import install_guards
from labs.shared.concurrency_lab import independent_factory,wait_blocked
from labs.shared.recovery_lab import restored_database
from labs.shared.performance_lab import explain,save_plans
spec=importlib.util.spec_from_file_location('independent_booking_feature',Path(__file__).with_name('feature.py'))
feature=importlib.util.module_from_spec(spec);sys.modules[spec.name]=feature;spec.loader.exec_module(feature)

def scenario(lab):
    ids=seed(lab);install_guards(lab);start=datetime(2026,11,1,10,tzinfo=timezone.utc);end=start+timedelta(hours=1)
    key=uuid4();body=dict(asset_id=str(ids['asset']),start=start.isoformat(),end=end.isoformat(),reason='Preventive inspection',request_key=str(key))
    with feature.feature_schema(lab):
        with lab.engine.connect() as c:
            check(c.exec_driver_sql(f'SELECT version FROM {lab.schema}.booking_revision').scalar_one()=='booking_v1','An explicit feature migration creates a recorded schema version before ORM use.')
            actual={row['name'] for row in inspect(c).get_columns('preventive_bookings',schema=lab.schema)}
            check(actual==set(feature.Booking.__table__.c.keys()),'The independently written migration and typed feature model agree on all stored/generated columns.')
        with TestClient(feature.create_booking_app(lab.session,lambda token:ids.get(token))) as api:
            check(api.get('/bookings').status_code==401,'The optional feature requires authentication.')
            check(api.post('/bookings',json=body,headers=headers('reporter')).status_code==403,'Students cannot schedule administrative preventive slots.')
            check(api.post('/bookings',json=body,headers=headers('other_admin')).status_code==404,'Another department cannot schedule the asset or reveal its details.')
            first=api.post('/bookings',json=body,headers=headers('admin'))
            check(first.status_code==201 and first.json()['version']==1,'Authorized scheduling commits a typed half-open interval and its audit event.')
            identity=UUID(first.json()['id'])
            check(api.post('/bookings',json=body,headers=headers('admin')).status_code==200,'An identical request key resolves the original durable booking rather than duplicating it.')
            check(api.post('/bookings',json={**body,'reason':'Different payload'},headers=headers('admin')).status_code==409,'Reusing an idempotency key for different content is rejected.')
            overlap={**body,'request_key':str(uuid4()),'start':(start+timedelta(minutes=30)).isoformat(),'end':(end+timedelta(minutes=30)).isoformat()}
            check(api.post('/bookings',json=overlap,headers=headers('admin')).status_code==409,'Database range exclusion rejects overlapping active bookings.')
            adjacent={**body,'request_key':str(uuid4()),'start':end.isoformat(),'end':(end+timedelta(hours=1)).isoformat()}
            check(api.post('/bookings',json=adjacent,headers=headers('admin')).status_code==201,'Half-open adjacent intervals are allowed without overlap.')
            check(api.post(f'/bookings/{identity}/cancel',json={'expected_version':99},headers=headers('admin')).status_code==409,'A stale cancellation version does not change the booking.')
            cancelled=api.post(f'/bookings/{identity}/cancel',json={'expected_version':1},headers=headers('admin'))
            check(cancelled.status_code==200 and cancelled.json()['version']==2,'Cancellation changes state/version atomically and releases the active exclusion slot.')
            check(api.post('/bookings',json={**body,'request_key':str(uuid4())},headers=headers('admin')).status_code==201,'A cancelled slot can be booked by a new durable request.')
            check(api.post('/bookings',json=body,headers=headers('admin')).json()['status']=='cancelled','The original idempotency key retains its original cancelled resource rather than creating a replacement.')
            check(api.get('/bookings',headers=headers('other_admin')).json()==[],'Booking list projections respect the recorded department scope.')
        held=Event();release=Event();started=Event();pids={};observer=lab.driver()
        with independent_factory(lab) as factory,ThreadPoolExecutor(max_workers=2) as executor:
            def book(number):
                try:
                    with factory() as s,s.begin():
                        pids[number]=s.scalar(text('SELECT pg_backend_pid()'))
                        if number==2:started.set()
                        result,_=feature.schedule(s,ids['admin'],ids['asset'],start+timedelta(days=1),end+timedelta(days=1),'Concurrent inspection',uuid4())
                        if number==1:
                            held.set()
                            if not release.wait(8):raise RuntimeError('Race release timed out')
                        return result['id']
                except IntegrityError as error:return error.orig.sqlstate
            first=executor.submit(book,1)
            try:
                if not held.wait(5):first.result(timeout=1);raise AssertionError('No held booking')
                second=executor.submit(book,2)
                if not started.wait(3):raise AssertionError('Contender not started')
                check(pids[1]!=pids[2] and wait_blocked(observer,pids[2],pids[1]),'Two independent scheduling transactions actually contend under the shared asset-lock protocol.')
            finally:release.set()
            check(first.result(timeout=8)!='23P01' and second.result(timeout=8)=='23P01','Only one concurrent overlapping booking commits; the exclusion constraint rejects the loser.')
        with lab.engine.begin() as c:
            check(c.exec_driver_sql(f'SELECT count(*) FROM {lab.schema}.preventive_bookings').scalar_one()==4,'Rejected and duplicate requests leave exactly four durable booking resources.')
            check(c.exec_driver_sql(f"SELECT count(*) FROM {lab.schema}.audit_events WHERE target_type='preventive_booking'").scalar_one()==5,'Four creations and one cancellation produce five successful audit events; conflicts leave none.')
            try:
                with c.begin_nested():c.exec_driver_sql(f"UPDATE {lab.schema}.preventive_bookings SET slot='empty'::tstzrange WHERE id=%s",(identity,))
            except IntegrityError:check(True,'Direct SQL cannot bypass the nonempty interval constraint.')
            else:raise AssertionError('Empty booking interval accepted')
            plan=explain(c,f"SELECT id FROM {lab.schema}.preventive_bookings WHERE status='scheduled' AND asset_span && int4range(1,1,'[]') AND slot && tstzrange('2026-11-01 10:00+00','2026-11-01 11:00+00','[)')")
            save_plans(80,booking_overlap=plan)
            snapshot=c.exec_driver_sql(f'SELECT id,status,version,slot::text FROM {lab.schema}.preventive_bookings ORDER BY id').all()
        with restored_database(lab,80) as target:
            with target.connect() as c:
                check(c.exec_driver_sql(f'SELECT id,status,version,slot::text FROM {lab.schema}.preventive_bookings ORDER BY id').all()==snapshot,'A real fresh-database restore preserves exact booking identities, versions, states and timezone instants.')
                check(c.exec_driver_sql('SELECT count(*) FROM pg_constraint WHERE connamespace=to_regnamespace(%s) AND contype=%s',(lab.schema,'x')).scalar_one()==1,'The restored feature retains its database exclusion constraint, not just application checks.')
        check(observer.execute(f'SELECT count(*) FROM {lab.schema}.booking_keys').fetchone()[0]==1,'Independent SQL verifies one stable asset key across all scheduling requests.')
    check(lab.driver().execute('SELECT to_regclass(%s)',(lab.schema+'.preventive_bookings',)).fetchone()[0] is None,'Feature teardown reverses only its optional migrated tables, preserving the core application schema.')

if __name__=='__main__':run(80,scenario)
