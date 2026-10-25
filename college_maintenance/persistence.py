"""Composable persistence primitives; callers validate business authorization."""
from contextlib import contextmanager
from sqlalchemy.exc import InvalidRequestError
from college_maintenance.models import Asset, AuditEvent, MaintenanceTicket
from college_maintenance.sessions import SessionFactory

@contextmanager
def unit_of_work(session):
    if session.in_transaction():
        raise InvalidRequestError('A transaction already exists; include earlier reads inside the owner or explicitly roll them back first.')
    with session.begin():
        yield session

def add_asset_row(session, *, code, name, department_id, category_id):
    asset=Asset(asset_code=code,name=name,department_id=department_id,category_id=category_id)
    session.add(asset);session.flush()
    return asset

def add_ticket_row(session, *, asset, actor_id, title, priority='high'):
    ticket=MaintenanceTicket(asset_id=asset.id,department_id=asset.department_id,reported_by_id=actor_id,
                             title=title,description='Reported with asset registration',priority=priority)
    session.add(ticket);session.flush()
    return ticket

def add_audit_row(session, *, actor_id, asset, ticket):
    entry=AuditEvent(actor_id=actor_id,asset_id=asset.id,ticket_id=ticket.id,action='asset_reported',payload={'asset_code':asset.asset_code})
    session.add(entry);session.flush()
    return entry

def record_asset_report(*, actor_id, department_id, category_id, code, name, title, session_factory=SessionFactory):
    """Own one persistence transaction after the caller validates permissions."""
    with session_factory() as session, unit_of_work(session):
        asset=add_asset_row(session,code=code,name=name,department_id=department_id,category_id=category_id)
        ticket=add_ticket_row(session,asset=asset,actor_id=actor_id,title=title)
        audit=add_audit_row(session,actor_id=actor_id,asset=asset,ticket=ticket)
        result={'asset_id':asset.id,'ticket_id':ticket.id,'audit_id':audit.id}
    return result
