"""Parent protection prevents concurrent existing/new line edits at completion."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import text,select,func
import psycopg
from college_maintenance.attachments import FileStore
from college_maintenance.completion import complete_in_session,complete_work_order
from college_maintenance.inventory import create_part,reconciliation_query
from college_maintenance.models import WorkOrderPart
from college_maintenance.repairs import set_part_line
from college_maintenance.workflow import Conflict
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed
from labs.shared.repair_lab import prepare
from labs.shared.history_lab import install_guards
from labs.shared.concurrency_lab import independent_factory,wait_blocked

def scenario(lab):
    ids=seed(lab);install_guards(lab)
    with TemporaryDirectory(dir=Path(__file__).resolve().parents[2]/'.local') as directory:
        store=FileStore(directory)
        with lab.session() as s,s.begin():
            part=create_part(s,ids['super'],sku='LOCK-PART',name='Part',unit_cost='10.00',opening=5).id
            extra=create_part(s,ids['super'],sku='NEW-LINE',name='Extra',unit_cost='20.00',opening=5).id
        _,order_id=prepare(lab,ids,store,[(part,1)])
        held=Event();release=Event();started={name:Event() for name in ('edit','insert')};pids={};observer=lab.driver()
        with independent_factory(lab) as factory,ThreadPoolExecutor(max_workers=3) as executor:
            def complete():
                with factory() as session,session.begin():
                    pids['complete']=session.scalar(text('SELECT pg_backend_pid()'))
                    def pause(stage):
                        if stage=='after_balances':
                            held.set()
                            if not release.wait(12):raise RuntimeError('Release timed out')
                    return complete_in_session(session,store,ids['tech'],order_id,stock_strategy='locked',_fault=pause)
            def edit(name,part_id,amount):
                try:
                    with factory() as session,session.begin():
                        pids[name]=session.scalar(text('SELECT pg_backend_pid()'));started[name].set()
                        set_part_line(session,ids['tech'],order_id,part_id,amount)
                except Conflict:return 'conflict'
                return 'unexpected success'
            completion=executor.submit(complete)
            try:
                if not held.wait(5):completion.result(timeout=1);raise AssertionError('No completion lock')
                editing=executor.submit(edit,'edit',part,2);inserting=executor.submit(edit,'insert',extra,1)
                for name in ('edit','insert'):
                    if not started[name].wait(3):raise AssertionError('No child editor')
                    check(wait_blocked(observer,pids[name],pids['complete']),f'Concurrent {name} waits on the completing parent protocol.')
            finally:release.set()
            result=completion.result(timeout=8)
            check(editing.result(timeout=8)==inserting.result(timeout=8)=='conflict','Both child writers recheck completed state after acquiring the parent and reject their edits.')
        with lab.session() as s:
            lines=s.scalars(select(WorkOrderPart).where(WorkOrderPart.work_order_id==order_id)).all()
            check(len(lines)==1 and lines[0].quantity_used==1 and lines[0].spare_part_id==part,'No edited or phantom part line bypasses completion protection.')
        try:observer.execute(f'INSERT INTO {lab.schema}.work_order_parts(work_order_id,spare_part_id,quantity_used,unit_cost_at_use) VALUES(%s,%s,1,20)',(order_id,extra))
        except psycopg.errors.CheckViolation:check(True,'The database guard also rejects a direct new child insert under completed work.')
        else:raise AssertionError('Direct child insert bypassed history guard')
        _,comparison=prepare(lab,ids,store,[(part,1)])
        guarded=complete_work_order(store,ids['tech'],comparison,session_factory=lab.session)
        check(guarded['total_cost']==result['total_cost']=='15.00','Sorted row locks and guarded arithmetic produce equivalent frozen cost results.')
        with lab.session() as s:
            check(all(row.stock_quantity==row.ledger_balance for row in s.execute(reconciliation_query())),'Both supported stock protocols preserve full reconciliation.')

if __name__=='__main__':run(44,scenario)
