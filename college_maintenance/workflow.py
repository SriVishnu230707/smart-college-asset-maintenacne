"""Authorized use cases. Call inside one outer Session transaction."""
from datetime import datetime, timezone
from sqlalchemy import select
from college_maintenance.models import Asset, Department, MaintenanceTicket, User, WorkOrder
from college_maintenance.reads import PRIORITIES, scope_for_actor

class NotFound(Exception): pass
class Conflict(Exception): pass

def nonblank(value, name, maximum=None):
    if not isinstance(value, str) or not value.strip() or (maximum and len(value) > maximum):
        raise ValueError(f'Invalid {name}')
    return value.strip()

def admin_scope(actor, department_id):
    if actor.role != 'super_admin' and not (actor.role == 'department_admin' and actor.department_id == department_id):
        raise PermissionError('Administrator scope required')

def can_read_ticket(actor, ticket):
    return (actor.role == 'super_admin' or ticket.reported_by_id == actor.user_id
        or actor.role == 'department_admin' and actor.department_id == ticket.department_id
        or actor.role == 'technician' and ticket.assigned_to_id == actor.user_id)

def locked_ticket(session, actor, ticket_id):
    ticket = session.scalar(select(MaintenanceTicket).where(MaintenanceTicket.id == ticket_id)
        .with_for_update().execution_options(populate_existing=True))
    if ticket is None or not can_read_ticket(actor, ticket): raise NotFound('Ticket not found')
    return ticket

def report_ticket(session, actor_id, *, asset_id, title, description, priority='medium'):
    actor = scope_for_actor(session, actor_id)
    asset = session.scalar(select(Asset).where(Asset.id == asset_id).with_for_update())
    if asset is None or actor.role != 'super_admin' and asset.department_id != actor.department_id:
        raise NotFound('Asset not found')
    if asset.status == 'retired' or session.get(Department, asset.department_id).is_archived:
        raise Conflict('Asset is ineligible for a new ticket')
    if priority not in PRIORITIES: raise ValueError('Invalid priority')
    ticket = MaintenanceTicket(asset_id=asset.id, department_id=asset.department_id, reported_by_id=actor.user_id,
        title=nonblank(title, 'title', 200), description=nonblank(description, 'description', 10000), priority=priority)
    session.add(ticket); session.flush()
    return ticket

def edit_report(session, actor_id, ticket_id, *, title, description):
    actor = scope_for_actor(session, actor_id); ticket = locked_ticket(session, actor, ticket_id)
    if ticket.reported_by_id != actor.user_id or actor.role != 'super_admin' and actor.department_id != ticket.department_id:
        raise PermissionError('Current-department reporter required')
    if ticket.status != 'open': raise Conflict('Original report is only editable while open')
    ticket.title = nonblank(title, 'title', 200); ticket.description = nonblank(description, 'description', 10000)
    session.flush(); return ticket

def triage_ticket(session, actor_id, ticket_id, priority):
    actor = scope_for_actor(session, actor_id); ticket = locked_ticket(session, actor, ticket_id)
    admin_scope(actor, ticket.department_id)
    if ticket.status not in {'open','assigned'}: raise Conflict('Ticket no longer permits triage')
    if priority not in PRIORITIES: raise ValueError('Invalid priority')
    ticket.priority = priority; session.flush(); return ticket

def ticket_result(ticket):
    return dict(id=ticket.id, asset_id=ticket.asset_id, department_id=ticket.department_id,
        reported_by_id=ticket.reported_by_id, assigned_to_id=ticket.assigned_to_id,
        title=ticket.title, description=ticket.description, priority=ticket.priority, status=ticket.status)

def transition_ticket(session, actor_id, ticket_id, *, action, technician_id=None, reason=None):
    actor = scope_for_actor(session, actor_id); ticket = locked_ticket(session, actor, ticket_id)
    admin_scope(actor, ticket.department_id)
    now = datetime.now(timezone.utc)
    orders = session.scalars(select(WorkOrder).where(WorkOrder.ticket_id == ticket.id)).all()
    if action == 'assign':
        if ticket.status not in {'open','assigned'} or orders:
            raise Conflict('Assignment requires open/assigned ticket with no existing work order')
        technician = session.scalar(select(User).where(User.id == technician_id).with_for_update())
        if technician is None or not technician.is_active or technician.role != 'technician' or technician.department_id != ticket.department_id:
            raise ValueError('Assignee must be an active technician in the recorded department')
        ticket.assigned_to_id = technician.id; ticket.assigned_at = now; ticket.status = 'assigned'
    elif action == 'reject':
        if ticket.status != 'open': raise Conflict('Only an open report can be rejected')
        ticket.rejection_reason = nonblank(reason, 'rejection reason', 10000)
        ticket.rejected_at = now; ticket.status = 'rejected'
    elif action in {'verify','rework'}:
        if ticket.status != 'awaiting_verification' or not any(o.status == 'completed' for o in orders) or any(o.status != 'completed' for o in orders):
            raise Conflict('Verification requires completed work and no active order')
        note = nonblank(reason, 'verification/rework reason', 10000)
        if action == 'verify':
            ticket.verification_note = note; ticket.closed_at = now; ticket.status = 'closed'
        else:
            ticket.rework_reason = note; ticket.status = 'in_progress'
    else: raise ValueError('Unsupported transition')
    session.flush(); return ticket
