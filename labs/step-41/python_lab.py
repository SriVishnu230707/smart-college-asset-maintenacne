"""Independent committed fingerprints prove atomicity at every fault boundary."""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy.exc import IntegrityError
from college_maintenance.attachments import FileStore
from college_maintenance.completion import complete_in_session,complete_work_order
from college_maintenance.database import engine
from college_maintenance.inventory import create_part,move_stock
from college_maintenance.models import InventoryMovement
from college_maintenance.repairs import set_part_line
from college_maintenance.workflow import Conflict
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed
from labs.shared.repair_lab import prepare
from labs.shared.history_lab import install_guards

def fingerprint(driver,schema):
    tables=['work_orders','maintenance_tickets','work_order_parts','spare_parts','inventory_movements','audit_events','work_order_attachments']
    entries=[]
    for table in tables:entries.extend([f"'{table}'",f"(SELECT coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]') FROM {schema}.{table} t)"])
    return driver.execute('SELECT jsonb_build_object('+','.join(entries)+')::text').fetchone()[0]

def scenario(lab):
    ids=seed(lab);install_guards(lab)
    with TemporaryDirectory(dir=Path(__file__).resolve().parents[2]/'.local') as directory:
        store=FileStore(directory)
        with lab.session() as s,s.begin():
            part=create_part(s,ids['super'],sku='FAIL-PART',name='Part',unit_cost='12.50',opening=5).id
            short=create_part(s,ids['super'],sku='SHORT-PART',name='Short part',unit_cost='4.00',opening=0).id
        ticket_id,order_id=prepare(lab,ids,store,[(part,2)])
        observer=lab.driver();baseline=fingerprint(observer,lab.schema)
        for stage in ('after_balances','after_ledger','before_completion','after_audit'):
            def fail(current):
                if current==stage:raise RuntimeError('synthetic fault: '+stage)
            try:
                with lab.session() as s,s.begin():complete_in_session(s,store,ids['tech'],order_id,_fault=fail)
            except RuntimeError as error:check(stage in str(error),f'The {stage} fault propagates to the transaction owner.')
            else:raise AssertionError('Fault swallowed')
            check(fingerprint(observer,lab.schema)==baseline,f'A fresh independent snapshot after {stage} matches all seven original tables.')
        try:
            with lab.session() as s,s.begin():
                def duplicate(stage):
                    if stage=='after_ledger':
                        s.add(InventoryMovement(spare_part_id=part,actor_id=ids['tech'],work_order_id=order_id,kind='consume',quantity_delta=-2));s.flush()
                complete_in_session(s,store,ids['tech'],order_id,_fault=duplicate)
        except IntegrityError as error:check(error.orig.sqlstate=='23505','A real duplicate-consumption constraint failure aborts the entire completion.')
        else:raise AssertionError('Duplicate ledger identity accepted')
        check(fingerprint(observer,lab.schema)==baseline,'Database failure preserves all pre-completion stock, cost, workflow and audit values.')
        with lab.session() as s,s.begin():set_part_line(s,ids['tech'],order_id,short,1)
        baseline=fingerprint(observer,lab.schema)
        try:complete_work_order(store,ids['tech'],order_id,session_factory=lab.session)
        except Conflict as error:check('Insufficient' in str(error),'One short part rejects the complete repair.')
        else:raise AssertionError('Short stock accepted')
        check(fingerprint(observer,lab.schema)==baseline,'A multi-part shortage consumes no other part and freezes no partial facts.')
        with lab.session() as s,s.begin():move_stock(s,ids['super'],short,kind='adjustment',delta=2,reason='Physical count correction')
        result=complete_work_order(store,ids['tech'],order_id,session_factory=lab.session)
        check(result['total_cost']=='34.00' and result['status']=='completed','A fresh attempt succeeds after an authorized balance correction.')
        check(engine.pool.checkedout()==0,'All success and failure transactions return their connection.')

if __name__=='__main__':run(41,scenario)
