"""Association rows carry quantity and historical unit cost, not just two FKs."""
import sys
from decimal import Decimal
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from college_maintenance.models import MaintenanceTicket, SparePart, WorkOrder, WorkOrderPart
from labs.shared.orm_lab import check, run

def scenario(lab):
    ids=lab.seed()
    with lab.session() as s,s.begin():
        ticket=MaintenanceTicket(asset_id=ids['asset'],reported_by_id=ids['reporter'],assigned_to_id=ids['tech'],department_id=ids['dept'],title='Repair',description='Part usage fixture',priority='high',status='assigned')
        part=SparePart(sku='NIC-001',name='Network card',current_unit_cost=Decimal('12.50'))
        order=WorkOrder(ticket=ticket,technician_id=ids['tech'])
        usage=WorkOrderPart(part=part,quantity_used=2,unit_cost_at_use=part.current_unit_cost)
        order.part_usages.append(usage);s.add(order);s.flush()
        order_id,part_id,ticket_id=order.id,part.id,ticket.id
        check(usage.work_order_id==order_id and usage.spare_part_id==part_id,'Association flush synchronizes both parent-generated keys.')
        check(usage.line_total==Decimal('25.00'),'Two units retain an exact 12.50 cost snapshot and a 25.00 line total.')
        check(usage.work_order is order and usage in part.usages,'Both association navigation paths refer to the same explicit usage object.')
        check(part.stock_quantity==0 and order.status=='draft','Draft usage does not reserve or consume inventory.')
    with lab.session() as s,s.begin():
        s.get(SparePart,part_id).current_unit_cost=Decimal('99.99')
    with lab.session() as s:
        usage=s.get(WorkOrderPart,(order_id,part_id))
        check(usage.unit_cost_at_use==Decimal('12.50') and usage.part.current_unit_cost==Decimal('99.99'),
              'Catalog price edits do not rewrite the historical usage price.')
        check(s.get(WorkOrder,order_id).part_usages[0].line_total==Decimal('25.00'),'Fresh relationship loading preserves the exact historical total.')
    cases=[
        (f'INSERT INTO {lab.schema}.work_order_parts VALUES (:order,:part,1,1.00)', '23505','Duplicate consolidated order/part lines are rejected.'),
        (f'UPDATE {lab.schema}.work_order_parts SET quantity_used=0 WHERE work_order_id=:order AND spare_part_id=:part','23514','Zero quantity is rejected by PostgreSQL.'),
        (f'UPDATE {lab.schema}.work_order_parts SET unit_cost_at_use=-0.01 WHERE work_order_id=:order AND spare_part_id=:part','23514','Negative historical unit cost is rejected by PostgreSQL.'),
    ]
    for sql,state,message in cases:
        with lab.engine.begin() as c:
            try:
                with c.begin_nested():c.execute(text(sql),{'order':order_id,'part':part_id})
            except IntegrityError as exc:check(exc.orig.sqlstate==state,message)
            else:raise AssertionError(message)
    with lab.engine.begin() as c:
        try:
            with c.begin_nested():c.execute(text(f'INSERT INTO {lab.schema}.work_orders (ticket_id,technician_id) VALUES (:ticket,:tech)'),{'ticket':ticket_id,'tech':ids['tech']})
        except IntegrityError as exc:check(exc.orig.sqlstate=='23505' and exc.orig.diag.constraint_name=='uq_work_orders_active_ticket','The partial unique index prevents two active work orders for one ticket.')
        else:raise AssertionError('Duplicate active work order accepted')
    check([c.key for c in inspect(WorkOrderPart).primary_key]==['work_order_id','spare_part_id'],'The association uses a composite work-order/part identity.')

if __name__=='__main__':run(24,scenario)
