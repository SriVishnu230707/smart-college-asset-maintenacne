"""Successful business events share their caller's transaction."""
from uuid import uuid4
from college_maintenance.models import AuditEvent

def audit_change(session, actor_id, action, *, ticket=None, target_type='ticket', target_id=None, request_id=None, details=None):
    event = AuditEvent(actor_id=actor_id, action=action, request_id=request_id or uuid4(),
        target_type=target_type, target_id=target_id or (ticket.id if ticket else None),
        ticket_id=ticket.id if ticket else None, asset_id=ticket.asset_id if ticket else None,
        department_id=ticket.department_id if ticket else None, payload=details or {})
    session.add(event); session.flush()
    return event
