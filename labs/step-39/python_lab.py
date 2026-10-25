"""Consolidated drafts reserve nothing; history cannot be rewritten."""
from datetime import datetime,timezone
import sys
from pathlib import Path
from uuid import UUID
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import select,func
import psycopg
from college_maintenance.database import engine
from college_maintenance.migrations import upgrade
from college_maintenance.models import SparePart,WorkOrder,WorkOrderPart,InventoryMovement
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed,client,headers,report
from labs.shared.history_lab import install_guards

def scenario(lab):
    ids=seed(lab);install_guards(lab)
    with client(lab,ids) as api:
        key=report(api,ids).json()['id']
        api.post(f'/tickets/{key}/transitions',headers=headers('admin'),json={'action':'assign','technician_id':str(ids['tech'])}).raise_for_status()
        part=api.post('/parts',headers=headers('super'),json={'sku':'DRAFT-PART','name':'Part','unit_cost':'12.50','opening':4}).json()['id']
        check(api.post(f'/tickets/{key}/work-orders',headers=headers('admin')).status_code==403,'Administrators cannot perform assigned technician repairs.')
        created=api.post(f'/tickets/{key}/work-orders',headers=headers('tech'))
        check(created.status_code==201,'The assigned technician may create a draft.')
        order=created.json()['id']
        check(api.post(f'/tickets/{key}/work-orders',headers=headers('tech')).status_code==409,'Only one draft/in-progress order may exist per ticket.')
        for amount in (1,3):api.put(f'/work-orders/{order}/parts/{part}',headers=headers('tech'),json={'quantity':amount}).raise_for_status()
        row=api.get(f'/work-orders/{order}',headers=headers('tech')).json()
        check(len(row['parts'])==1 and row['parts'][0]['quantity_used']==3,'Repeated part edits consolidate one composite-identity line.')
        with lab.session() as s:
            check(s.get(SparePart,UUID(part)).stock_quantity==4 and s.scalar(select(func.count()).select_from(InventoryMovement))==1,'Draft quantities reserve no stock and create no consumption movement.')
        check(api.post(f'/work-orders/{order}/start',headers=headers('tech')).json()['status']=='in_progress','Starting the draft starts its ticket repair.')
        check(api.delete(f'/work-orders/{order}',headers=headers('tech')).status_code==409,'Started repairs cannot be discarded.')
        check(api.patch(f'/work-orders/{order}',headers=headers('tech'),json={'labor_cost':'1.001','completion_note':'Done'}).status_code==400,'Draft monetary edits reject excess precision.')
        api.patch(f'/work-orders/{order}',headers=headers('tech'),json={'labor_cost':'5.00','completion_note':'Done'}).raise_for_status()
        # A synthetic completed fixture isolates immutability; atomic completion is Step 40.
        with lab.session() as s,s.begin():
            completed=s.get(WorkOrder,UUID(order));completed.status='completed';completed.completed_at=datetime.now(timezone.utc)
            s.get(SparePart,UUID(part)).current_unit_cost='99.99'
        check(api.get(f'/work-orders/{order}',headers=headers('admin')).json()['parts'][0]['unit_cost_at_use']=='12.50','A catalog price change does not rewrite the stored historical line cost.')
        check(api.patch(f'/work-orders/{order}',headers=headers('tech'),json={'labor_cost':'7.00','completion_note':'Rewrite'}).status_code==409,'Completed orders reject service-layer edits.')
    driver=lab.driver()
    for table,sql in [('work_orders',"SET labor_cost=9"),('work_order_parts','SET quantity_used=2')]:
        try:driver.execute(f'UPDATE {lab.schema}.{table} {sql} WHERE '+('id' if table=='work_orders' else 'work_order_id')+'=%s',(UUID(order),))
        except psycopg.errors.CheckViolation:check(True,f'Direct SQL cannot rewrite completed {table} facts.')
        else:raise AssertionError('Completed history rewritten')
    for table in ('audit_events','inventory_movements'):
        try:driver.execute(f'DELETE FROM {lab.schema}.{table}')
        except psycopg.errors.CheckViolation:check(True,f'Direct SQL cannot delete append-only {table}.')
        else:raise AssertionError('Append-only history deleted')
    with engine.begin() as c:upgrade(c)

if __name__=='__main__':run(39,scenario)
