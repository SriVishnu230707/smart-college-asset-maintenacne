"""One atomic repair completion; no editable fields enter this command."""
from datetime import datetime, timezone
import json
from sqlalchemy import select
from college_maintenance.models import WorkOrderPart, WorkOrderAttachment, SparePart, InventoryMovement
from college_maintenance.reads import scope_for_actor
from college_maintenance.attachments import order_parent
from college_maintenance.workflow import Conflict, nonblank
from college_maintenance.inventory import money,consume_guarded
from college_maintenance.auditing import audit_change
from college_maintenance.sessions import SessionFactory
from college_maintenance.retries import retry_transaction

def completed_result(session, order):
    lines=session.scalars(select(WorkOrderPart).where(WorkOrderPart.work_order_id==order.id).order_by(WorkOrderPart.spare_part_id)).all()
    parts=[dict(spare_part_id=line.spare_part_id,quantity_used=line.quantity_used,
        unit_cost_at_use=format(line.unit_cost_at_use,'.2f'),line_total=format(line.line_total,'.2f')) for line in lines]
    parts_cost=sum((line.line_total for line in lines),money('0.00'))
    return dict(work_order_id=order.id,ticket_id=order.ticket_id,technician_id=order.technician_id,status=order.status,
        completed_at=order.completed_at,currency='INR',labor_cost=format(order.labor_cost,'.2f'),parts=parts,
        parts_cost=format(parts_cost,'.2f'),total_cost=format(order.labor_cost+parts_cost,'.2f'))

def complete_in_session(session,store,actor_id,order_id,request_id=None,*,_fault=None,stock_strategy='guarded'):
    # Private fault seam for real-transaction tests; never accepted from HTTP.
    def checkpoint(stage):
        if _fault is not None:_fault(stage)
    actor=scope_for_actor(session,actor_id)
    ticket,order=order_parent(session,actor,order_id,write=True)
    if order.status!='in_progress' or ticket.status!='in_progress':raise Conflict('Only an in-progress repair can complete')
    nonblank(order.completion_note,'completion note',10000);money(order.labor_cost)
    proofs=session.scalars(select(WorkOrderAttachment).where(WorkOrderAttachment.work_order_id==order.id)).all()
    if not proofs:raise Conflict('Completion requires work-order proof')
    for proof in proofs:store.read(proof)
    lines=session.scalars(select(WorkOrderPart).where(WorkOrderPart.work_order_id==order.id).order_by(WorkOrderPart.spare_part_id)).all()
    if stock_strategy not in {'guarded','locked'}:raise ValueError('Unknown stock strategy')
    parts={}
    if stock_strategy=='locked':
        part_ids=[line.spare_part_id for line in lines]
        parts={p.id:p for p in session.scalars(select(SparePart).where(SparePart.id.in_(part_ids)).order_by(SparePart.id).with_for_update().execution_options(populate_existing=True))}
    total=order.labor_cost
    for line in lines:
        if stock_strategy=='guarded':cost=consume_guarded(session,line.spare_part_id,line.quantity_used)
        else:
            part=parts.get(line.spare_part_id)
            if part is None or part.is_archived:raise Conflict('A required part is unavailable')
            if part.stock_quantity<line.quantity_used:raise Conflict('Insufficient stock')
            part.stock_quantity-=line.quantity_used;cost=part.current_unit_cost
        line.unit_cost_at_use=money(cost);total+=line.unit_cost_at_use*line.quantity_used
    money(total)  # Guarded updates also roll back if final totals cannot fit.
    session.flush()
    checkpoint('after_balances')
    for line in lines:
        session.add(InventoryMovement(spare_part_id=line.spare_part_id,actor_id=actor_id,work_order_id=order.id,kind='consume',quantity_delta=-line.quantity_used))
    # Flush child snapshots while their protected parent is still unfinished.
    session.flush()
    checkpoint('after_ledger')
    checkpoint('before_completion')
    order.status='completed';order.completed_at=datetime.now(timezone.utc);ticket.status='awaiting_verification'
    session.flush()
    result=completed_result(session,order)
    audit_change(session,actor_id,'work_order_completed',ticket=ticket,target_type='work_order',target_id=order.id,request_id=request_id,
        details={**json.loads(json.dumps(result,default=str)),'proofs':[dict(id=str(p.id),sha256=p.sha256) for p in proofs]})
    checkpoint('after_audit')
    return result

def complete_work_order(store,actor_id,order_id,*,session_factory=SessionFactory,request_id=None,stock_strategy='guarded'):
    return retry_transaction(lambda session:complete_in_session(session,store,actor_id,order_id,
        request_id=request_id,stock_strategy=stock_strategy),session_factory=session_factory)
