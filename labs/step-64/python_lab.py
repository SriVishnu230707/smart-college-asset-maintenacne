"""Capstone composes an actual contention proof, HTTP closure, and recovery."""
from pathlib import Path
from datetime import datetime,date,timezone,timedelta
import importlib.util,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import text
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import client,headers
from labs.shared.recovery_lab import restored_database

def rebuilt_total(connection,schema):
    # Independently expressed scalar child aggregate avoids both parts and
    # comments fan-out; deliberately does not call the application report.
    return connection.execute(text(f'''SELECT coalesce(sum(w.labor_cost+coalesce((SELECT sum(p.quantity_used*p.unit_cost_at_use)
        FROM {schema}.work_order_parts p WHERE p.work_order_id=w.id),0)),0)
        FROM {schema}.work_orders w WHERE w.status='completed' ''')).scalar_one()

def scenario(lab):
    source=Path(__file__).resolve().parents[1]/'step-43/python_lab.py'
    spec=importlib.util.spec_from_file_location('capstone_real_stock_race',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.scenario(lab)  # real distinct backends and observed lock wait
    observer=lab.driver()
    users=observer.execute(f'SELECT email,id FROM {lab.schema}.users').fetchall()
    ids={email.split('@')[0]:identity for email,identity in users}
    ticket,order=observer.execute(f"SELECT ticket_id,id FROM {lab.schema}.work_orders WHERE status='completed'").fetchone()
    with client(lab,ids) as api:
        before=api.post(f'/work-orders/{order}/complete',headers=headers('tech'))
        check(before.status_code==200 and before.json()['total_cost']=='15.00','The completed repair result can be retrieved again without consuming another part.')
        verified=api.post(f'/tickets/{ticket}/transitions',headers=headers('admin'),json={'action':'verify','reason':'Capstone accepted'})
        check(verified.status_code==200 and verified.json()['status']=='closed','The scoped administrator verifies and closes the winning ticket.')
        check(api.post(f'/work-orders/{order}/complete',headers=headers('tech')).json()==before.json(),'Closed-ticket completion retries return the original immutable outcome.')
        check(api.get('/reports/costs',headers=headers('admin')).json()[0]['total_cost']=='15.00','The authorized department cost report includes exactly one winning repair.')
        check(len(api.get('/reports/ranked-failures',headers=headers('admin')).json())==1,'The window report is integrated through an authorized HTTP projection.')
        check(api.get('/reports/ranked-failures',params={'limit':0},headers=headers('admin')).status_code==422,'Ranked HTTP reporting enforces its row budget independently of rank/tie selection.')
        now=datetime.now(timezone(timedelta(hours=5,minutes=30)));start=date(now.year,now.month,1);end=date(now.year+(now.month==12),now.month%12+1,1)
        report=api.get('/reports/monthly-costs',params={'start':start.isoformat(),'end':end.isoformat()},headers=headers('admin'))
        check(report.status_code==200 and report.json()[0]['cost']=='15.00','Monthly HTTP reporting preserves exact decimal strings and complete month grain.')
        check(api.get('/reports/monthly-costs',params={'start':start.isoformat(),'end':end.isoformat()},headers=headers('reporter')).status_code==403,'New analytical routes retain report-role restrictions.')
        audit=api.get(f'/tickets/{ticket}/audit',headers=headers('admin')).json()
        check(sum(row['action']=='work_order_completed' for row in audit)==1,'The audit journey explains one durable completion despite retries.')
    with lab.engine.connect() as c:check(rebuilt_total(c,lab.schema)==15,'An independently rebuilt SQL cost expression matches the application result.')
    with restored_database(lab,64) as target:
        with target.connect() as c:check(rebuilt_total(c,lab.schema)==15,'The same independent report matches after a real fresh-database dump/restore.')
    check(observer.execute(f"SELECT count(*) FROM {lab.schema}.inventory_movements WHERE kind='consume'").fetchone()[0]==1,'Independent SQL confirms one consumption after closure, retries and recovery.')
    print('Core acceptance complete. Step 62 separately proves fresh container startup and network HTTP; Step 63 verifies separately restored attachment bytes. Existing contention logic is reused, while the independent cost proof is rebuilt here.')

if __name__=='__main__':run(64,scenario)
