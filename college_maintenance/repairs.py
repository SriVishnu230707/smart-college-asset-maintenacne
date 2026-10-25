"""Work-order commands share ticket -> order -> sorted parts locking."""
from sqlalchemy import select, delete
from college_maintenance.models import WorkOrder, WorkOrderPart, WorkOrderAttachment, SparePart
from college_maintenance.reads import scope_for_actor
from college_maintenance.workflow import Conflict, NotFound, locked_ticket, nonblank
from college_maintenance.attachments import order_parent
from college_maintenance.inventory import money, quantity
from college_maintenance.auditing import audit_change

def create_order(session, actor_id, ticket_id, request_id=None):
    actor=scope_for_actor(session,actor_id);ticket=locked_ticket(session,actor,ticket_id)
    if actor.role!='technician' or ticket.assigned_to_id!=actor_id:raise PermissionError('Assigned technician required')
    if ticket.status not in {'assigned','in_progress'}:raise Conflict('Ticket does not permit repair')
    if session.scalar(select(WorkOrder.id).where(WorkOrder.ticket_id==ticket.id,WorkOrder.status.in_(['draft','in_progress']))):
        raise Conflict('An active work order already exists')
    order=WorkOrder(ticket_id=ticket.id,technician_id=actor_id);session.add(order);session.flush()
    audit_change(session,actor_id,'work_order_created',ticket=ticket,target_type='work_order',target_id=order.id,request_id=request_id)
    return order

def start_order(session,actor_id,order_id,request_id=None):
    actor=scope_for_actor(session,actor_id);ticket,order=order_parent(session,actor,order_id,write=True)
    if order.status!='draft':raise Conflict('Only a draft can start')
    order.status='in_progress';ticket.status='in_progress';session.flush()
    audit_change(session,actor_id,'work_order_started',ticket=ticket,target_type='work_order',target_id=order.id,request_id=request_id)
    return order

def edit_order(session,actor_id,order_id,*,labor_cost,completion_note,request_id=None):
    actor=scope_for_actor(session,actor_id);ticket,order=order_parent(session,actor,order_id,write=True)
    order.labor_cost=money(labor_cost)
    order.completion_note=nonblank(completion_note,'completion note',10000) if completion_note is not None else None
    session.flush()
    audit_change(session,actor_id,'work_order_edited',ticket=ticket,target_type='work_order',target_id=order.id,request_id=request_id)
    return order

def set_part_line(session,actor_id,order_id,part_id,amount,request_id=None):
    actor=scope_for_actor(session,actor_id);ticket,order=order_parent(session,actor,order_id,write=True)
    quantity(amount)
    part=session.scalar(select(SparePart).where(SparePart.id==part_id).with_for_update())
    if part is None:raise NotFound('Part not found')
    if part.is_archived:raise Conflict('Archived parts cannot be selected')
    line=session.get(WorkOrderPart,(order.id,part.id))
    if line is None:
        line=WorkOrderPart(work_order_id=order.id,spare_part_id=part.id,quantity_used=amount,unit_cost_at_use=part.current_unit_cost);session.add(line)
    else:line.quantity_used=amount;line.unit_cost_at_use=part.current_unit_cost
    session.flush()
    audit_change(session,actor_id,'work_order_part_set',ticket=ticket,target_type='work_order',target_id=order.id,request_id=request_id,details={'part_id':str(part.id),'quantity':amount})
    return order

def remove_part_line(session,actor_id,order_id,part_id,request_id=None):
    actor=scope_for_actor(session,actor_id);ticket,order=order_parent(session,actor,order_id,write=True)
    line=session.get(WorkOrderPart,(order.id,part_id))
    if line is None:raise NotFound('Part line not found')
    session.delete(line);session.flush()
    audit_change(session,actor_id,'work_order_part_removed',ticket=ticket,target_type='work_order',target_id=order.id,request_id=request_id,details={'part_id':str(part_id)})
    return order

def discard_order(session,actor_id,order_id,request_id=None):
    actor=scope_for_actor(session,actor_id);ticket,order=order_parent(session,actor,order_id,write=True)
    if order.status!='draft':raise Conflict('Started repairs cannot be discarded')
    session.execute(delete(WorkOrderAttachment).where(WorkOrderAttachment.work_order_id==order.id))
    session.execute(delete(WorkOrderPart).where(WorkOrderPart.work_order_id==order.id))
    session.delete(order);session.flush()
    audit_change(session,actor_id,'work_order_discarded',ticket=ticket,target_type='work_order',target_id=order_id,request_id=request_id)
    return {'discarded':order_id}

def order_result(session,order):
    lines=session.scalars(select(WorkOrderPart).where(WorkOrderPart.work_order_id==order.id).order_by(WorkOrderPart.spare_part_id)).all()
    return dict(id=order.id,ticket_id=order.ticket_id,technician_id=order.technician_id,status=order.status,
        labor_cost=format(order.labor_cost,'.2f'),completion_note=order.completion_note,completed_at=order.completed_at,
        parts=[dict(spare_part_id=line.spare_part_id,quantity_used=line.quantity_used,unit_cost_at_use=format(line.unit_cost_at_use,'.2f')) for line in lines])
