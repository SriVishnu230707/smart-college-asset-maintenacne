"""Declared-grain reports: part/order aggregates precede department joins."""
from decimal import Decimal
from sqlalchemy import select,func,true
from college_maintenance.models import Department,Asset,MaintenanceTicket,WorkOrder,WorkOrderPart

def report_scope(scope,department_column):
    if scope.role=='super_admin':return true()
    if scope.role=='department_admin':return department_column==scope.department_id
    raise PermissionError('Maintenance reports require scoped administration')

def completed_order_costs():
    """One row per completed order; parts are first reduced to that grain."""
    parts=select(WorkOrderPart.work_order_id,func.sum(WorkOrderPart.quantity_used*WorkOrderPart.unit_cost_at_use).label('parts_cost')).group_by(WorkOrderPart.work_order_id).subquery('parts_per_order')
    return (select(WorkOrder.id.label('work_order_id'),MaintenanceTicket.department_id,
        (WorkOrder.labor_cost+func.coalesce(parts.c.parts_cost,Decimal('0.00'))).label('total_cost'))
        .select_from(WorkOrder).join(MaintenanceTicket,MaintenanceTicket.id==WorkOrder.ticket_id)
        .outerjoin(parts,parts.c.work_order_id==WorkOrder.id).where(WorkOrder.status=='completed'))

def costs_by_department_query(scope):
    orders=completed_order_costs().subquery('completed_order_costs')
    totals=select(orders.c.department_id,func.sum(orders.c.total_cost).label('total_cost'),func.count().label('completed_orders')).group_by(orders.c.department_id).subquery('department_costs')
    return (select(Department.id.label('department_id'),Department.code,
        func.coalesce(totals.c.total_cost,Decimal('0.00')).label('total_cost'),func.coalesce(totals.c.completed_orders,0).label('completed_orders'))
        .select_from(Department).outerjoin(totals,totals.c.department_id==Department.id)
        .where(report_scope(scope,Department.id)).order_by(Department.code))

def failure_frequency_query(scope):
    """One row per recorded department/asset; count reports, not repairs."""
    return (select(MaintenanceTicket.department_id,Asset.id.label('asset_id'),Asset.asset_code,func.count(MaintenanceTicket.id).label('ticket_count'))
        .select_from(MaintenanceTicket).join(Asset,Asset.id==MaintenanceTicket.asset_id)
        .where(report_scope(scope,MaintenanceTicket.department_id))
        .group_by(MaintenanceTicket.department_id,Asset.id,Asset.asset_code)
        .order_by(func.count(MaintenanceTicket.id).desc(),MaintenanceTicket.department_id,Asset.id))

def cost_rows(session,scope,limit=100):
    return [{**dict(row),'total_cost':format(row['total_cost'],'.2f'),'currency':'INR'} for row in session.execute(costs_by_department_query(scope).limit(limit)).mappings()]
