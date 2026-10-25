"""Prove one successful complete repair and its independent persisted facts."""
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import select
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from college_maintenance.database import engine
from college_maintenance.models import Base
from college_maintenance.models import SparePart,InventoryMovement,AuditEvent,WorkOrder,MaintenanceTicket
from college_maintenance.inventory import create_part
from college_maintenance.attachments import FileStore
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed,client,headers
from labs.shared.repair_lab import prepare
from labs.shared.history_lab import install_guards

def scenario(lab):
    ids=seed(lab);install_guards(lab)
    with TemporaryDirectory(dir=Path(__file__).resolve().parents[2]/'.local') as directory:
        store=FileStore(directory)
        with lab.session() as s,s.begin():part_id=create_part(s,ids['super'],sku='REPAIR-PART',name='Part',unit_cost='12.50',opening=5).id
        ticket_id,order_id=prepare(lab,ids,store,[(part_id,2)])
        with lab.session() as s,s.begin():s.get(SparePart,part_id).current_unit_cost='15.00'
        with client(lab,ids,storage=store) as api:
            check(api.post(f'/work-orders/{order_id}/complete',headers=headers('admin')).status_code==403,'Administrators may verify repairs but cannot initiate technician completion.')
            check(api.post(f'/work-orders/{order_id}/complete',headers=headers('tech'),json={'labor_cost':'0.00'}).status_code==422,'Completion accepts no editable cost or part fields.')
            response=api.post(f'/work-orders/{order_id}/complete',headers=headers('tech'))
            check(response.status_code==200,'One authorized completion succeeds through the API boundary.')
            result=response.json()
            check(result['status']=='completed' and result['currency']=='INR' and result['total_cost']=='35.00','The completion result contains exact frozen INR totals.')
            check(result['parts'][0]['unit_cost_at_use']=='15.00','Part cost is captured at successful completion, replacing the draft estimate.')
            check(api.post(f'/tickets/{ticket_id}/transitions',headers=headers('admin'),json={'action':'verify','reason':'Verified'}).json()['status']=='closed','Completed work can be verified through the declared final transition.')
            check(api.put(f'/work-orders/{order_id}/parts/{part_id}',headers=headers('tech'),json={'quantity':1}).status_code==409,'Completed line edits cannot change frozen consumption.')
        driver=lab.driver()
        check(driver.execute(f'SELECT stock_quantity,(SELECT sum(quantity_delta) FROM {lab.schema}.inventory_movements WHERE spare_part_id=%s) FROM {lab.schema}.spare_parts WHERE id=%s',(part_id,part_id)).fetchone()==(3,3),'Independent stock and ledger both retain the same remaining balance.')
        with lab.session() as s:
            movement=s.scalars(select(InventoryMovement).where(InventoryMovement.kind=='consume')).one()
            check(movement.work_order_id==order_id and movement.quantity_delta==-2,'Consumption references the completed order and exact frozen quantity.')
            event=s.scalars(select(AuditEvent).where(AuditEvent.action=='work_order_completed')).one()
            check(event.payload['total_cost']=='35.00' and event.payload['proofs'],'The single success audit event retains frozen costs and verified proof identity.')
            check(s.get(WorkOrder,order_id).completed_at is not None and s.get(MaintenanceTicket,ticket_id).status=='closed','Completion timestamp and verified ticket state persist together.')
        _,labor_order=prepare(lab,ids,store,labor='0.00')
        with client(lab,ids,storage=store) as api:
            response=api.post(f'/work-orders/{labor_order}/complete',headers=headers('tech'))
            check(response.status_code==200 and response.json()['total_cost']=='0.00' and response.json()['parts']==[],'A zero-cost labor-only repair with proof is valid.')
    with engine.connect() as connection:
        changes=compare_metadata(MigrationContext.configure(connection,opts={'compare_type':True,'compare_server_default':True}),Base.metadata)
        check(not changes,f'The workflow migration head matches the complete ORM metadata: {changes}.')

if __name__=='__main__':run(40,scenario)
