"""Same-order requests converge on durable frozen results, including rollback."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import text,select,func
from college_maintenance.attachments import FileStore
from college_maintenance.completion import complete_in_session,complete_work_order
from college_maintenance.inventory import create_part,reconciliation_query
from college_maintenance.models import SparePart,InventoryMovement,AuditEvent
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed,client,headers
from labs.shared.repair_lab import prepare
from labs.shared.history_lab import install_guards
from labs.shared.concurrency_lab import independent_factory,wait_blocked

def scenario(lab):
    ids=seed(lab);install_guards(lab)
    with TemporaryDirectory(dir=Path(__file__).resolve().parents[2]/'.local') as directory:
        store=FileStore(directory)
        with lab.session() as s,s.begin():part=create_part(s,ids['super'],sku='RETRY-PART',name='Part',unit_cost='10.00',opening=4).id
        ticket_id,order_id=prepare(lab,ids,store,[(part,1)])
        observer=lab.driver()
        def race(order,rollback_first=False):
            held=Event();release=Event();started=Event();pids={}
            with independent_factory(lab) as factory,ThreadPoolExecutor(max_workers=2) as executor:
                def first():
                    try:
                        with factory() as s,s.begin():
                            pids['first']=s.scalar(text('SELECT pg_backend_pid()'))
                            def pause(stage):
                                if stage=='after_balances':
                                    held.set()
                                    if not release.wait(12):raise RuntimeError('Release timed out')
                                    if rollback_first:raise RuntimeError('synthetic first completion rollback')
                            return complete_in_session(s,store,ids['tech'],order,_fault=pause)
                    except RuntimeError:
                        if rollback_first:return 'rolled back'
                        raise
                def second():
                    with factory() as s,s.begin():
                        pids['second']=s.scalar(text('SELECT pg_backend_pid()'));started.set()
                        return complete_in_session(s,store,ids['tech'],order)
                a=executor.submit(first)
                try:
                    if not held.wait(5):a.result(timeout=1);raise AssertionError('No held completion')
                    b=executor.submit(second)
                    if not started.wait(3):raise AssertionError('No duplicate caller')
                    check(wait_blocked(observer,pids['second'],pids['first']),'A duplicate completion waits for the same protected work-order operation.')
                finally:release.set()
                return a.result(timeout=8),b.result(timeout=8)
        first,second=race(order_id)
        check(first==second,'Simultaneous authorized callers receive the exact same frozen completed result.')
        # Discard the first response, then resolve the same durable operation again.
        recovered=complete_work_order(store,ids['tech'],order_id,session_factory=lab.session)
        check(recovered==first,'A retry after a discarded success response resolves the existing durable outcome.')
        with lab.session() as s,s.begin():s.get(SparePart,part).current_unit_cost='99.99'
        with client(lab,ids,storage=store) as api:
            original=api.post(f'/work-orders/{order_id}/complete',headers=headers('tech')).json()
            admin=api.post(f'/work-orders/{order_id}/complete',headers=headers('admin'))
            check(admin.status_code==200 and admin.json()==original,'A scoped administrator may retrieve an existing completion without initiating unfinished repairs.')
            check(api.post(f'/work-orders/{order_id}/complete',headers=headers('reporter')).status_code==403,'A ticket reporter cannot reveal financial completion results.')
            check(api.post(f'/work-orders/{order_id}/complete',headers=headers('other_admin')).status_code==404,'An out-of-scope administrator cannot reveal a durable result.')
            api.post(f'/tickets/{ticket_id}/transitions',headers=headers('admin'),json={'action':'rework','reason':'Another repair is needed'}).raise_for_status()
            check(api.post(f'/work-orders/{order_id}/complete',headers=headers('tech')).json()==original,'Retry checks the existing completion before unfinished ticket-state rules, even after rework.')
        other_ticket,other_order=prepare(lab,ids,store,[(part,1)])
        rolled_back,winner=race(other_order,True)
        check(rolled_back=='rolled back' and winner['status']=='completed','A waiting duplicate may become the first successful completion when the earlier transaction rolls back.')
        with client(lab,ids,storage=store) as api:
            api.post(f'/tickets/{other_ticket}/transitions',headers=headers('admin'),json={'action':'verify','reason':'Verified'}).raise_for_status()
            check(api.post(f'/work-orders/{other_order}/complete',headers=headers('tech')).json()['total_cost']==winner['total_cost'],'A later closed ticket still permits retrieval of its original immutable completion.')
        with lab.session() as s:
            for key in (order_id,other_order):
                check(s.scalar(select(func.count()).select_from(InventoryMovement).where(InventoryMovement.work_order_id==key))==1,'Each work-order/part has one durable consumption movement.')
                check(s.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.target_id==key,AuditEvent.action=='work_order_completed'))==1,'Each completed operation has one success audit, regardless of retries.')
            check(s.get(SparePart,part).stock_quantity==2 and all(row.stock_quantity==row.ledger_balance for row in s.execute(reconciliation_query())),'Duplicate and rolled-back callers cause no additional stock consumption.')

if __name__=='__main__':run(47,scenario)
