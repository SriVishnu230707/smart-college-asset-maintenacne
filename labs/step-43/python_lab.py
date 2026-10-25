"""Two technicians really contend for one unit through completion services."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import text,select,func
from college_maintenance.attachments import FileStore
from college_maintenance.completion import complete_in_session
from college_maintenance.inventory import create_part,guarded_stock_statement
from college_maintenance.models import User,InventoryMovement,AuditEvent,WorkOrder,SparePart
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
            part=create_part(s,ids['super'],sku='LAST-UNIT',name='Last unit',unit_cost='10.00',opening=1).id
            tech=User(email='second-tech@example.test',display_name='Second technician',password_hash='synthetic_only',role='technician',department_id=ids['dept'])
            s.add(tech);s.flush();second_tech=tech.id
        _,first_order=prepare(lab,ids,store,[(part,1)])
        _,second_order=prepare(lab,{**ids,'tech':second_tech},store,[(part,1)])
        print('Guarded SQL:',guarded_stock_statement(part,1))
        try:guarded_stock_statement(part,0)
        except ValueError:check(True,'The guarded persistence expression rejects nonpositive quantities before SQL.')
        else:raise AssertionError('Zero consumption accepted')
        held=Event();release=Event();started=Event();pids={};observer=lab.driver()
        with independent_factory(lab) as factory,ThreadPoolExecutor(max_workers=2) as executor:
            def winner():
                with factory() as session,session.begin():
                    pids['first']=session.scalar(text('SELECT pg_backend_pid()'))
                    def pause(stage):
                        if stage=='after_balances':
                            held.set()
                            if not release.wait(5):raise RuntimeError('Test release timed out')
                    return complete_in_session(session,store,ids['tech'],first_order,_fault=pause)
            def contender():
                try:
                    with factory() as session,session.begin():
                        pids['second']=session.scalar(text('SELECT pg_backend_pid()'));started.set()
                        return complete_in_session(session,store,second_tech,second_order)
                except Conflict as error:return str(error)
            first=executor.submit(winner)
            try:
                if not held.wait(5):first.result(timeout=1);raise AssertionError('Winner never held stock')
                second=executor.submit(contender)
                if not started.wait(3):raise AssertionError('Contender did not connect')
                check(pids['first']!=pids['second'],'Competing completions use distinct physical backends, not the one-slot learning pool.')
                check(wait_blocked(observer,pids['second'],pids['first']),'PostgreSQL confirms that the second guarded UPDATE waits on the first transaction.')
            finally:release.set()
            result=first.result(timeout=8);loser=second.result(timeout=8)
            check(result['status']=='completed' and 'Insufficient stock' in loser,'Exactly one last-unit completion commits; the other observes the rechecked stock predicate.')
        with lab.session() as s:
            check(s.get(SparePart,part).stock_quantity==0,'The final balance is zero rather than negative.')
            check(s.scalar(select(func.count()).select_from(InventoryMovement).where(InventoryMovement.kind=='consume'))==1,'Exactly one consumption identity is durable.')
            check(s.get(WorkOrder,first_order).status=='completed' and s.get(WorkOrder,second_order).status=='in_progress','The losing work order retains its pre-completion state.')
            check(s.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action=='work_order_completed'))==1,'The losing transaction leaves no success audit event.')
        with lab.session() as s,s.begin():
            check(s.scalar(select(func.sum(InventoryMovement.quantity_delta)).where(InventoryMovement.spare_part_id==part))==0,'Opening plus winning consumption reconciles to the stored balance.')

if __name__=='__main__':run(43,scenario)
