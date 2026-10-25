"""Explicit projections and server-derived read scopes; no ORM objects escape."""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from sqlalchemy import or_, select, true
from sqlalchemy.orm import aliased
from college_maintenance.models import Asset, AssetCategory, Department, MaintenanceTicket, User

STATUSES=frozenset({'open','assigned','in_progress','awaiting_verification','closed','rejected'})
PRIORITIES=frozenset({'low','medium','high','critical'})

@dataclass(frozen=True)
class ReadScope:
    user_id:UUID
    role:str
    department_id:UUID | None

def scope_for_actor(session, actor_id):
    """actor_id must come from the later authentication boundary, not a request role."""
    actor=session.get(User,actor_id)
    if actor is None or not actor.is_active:raise PermissionError('Inactive or missing actor')
    if actor.role not in {'student','technician','department_admin','super_admin'}:raise PermissionError('Unknown actor role')
    return ReadScope(actor.id,actor.role,actor.department_id)

@dataclass(frozen=True)
class AssetDetail:
    id:UUID
    asset_code:str
    name:str
    department_code:str
    category_code:str
    status:str
    location:str | None
    condition_note:str

@dataclass(frozen=True)
class TicketView:
    id:UUID
    title:str
    asset_id:UUID
    department_id:UUID
    reported_by_id:UUID
    assigned_to_id:UUID | None
    status:str
    priority:str
    created_at:datetime
    reporter_name:str
    assignee_name:str | None

def asset_detail(session, scope, asset_id):
    allowed=true() if scope.role=='super_admin' else Asset.department_id==scope.department_id
    statement=select(Asset.id,Asset.asset_code,Asset.name,Department.code.label('department_code'),AssetCategory.code.label('category_code'),
        Asset.status,Asset.location,Asset.condition_note).join(Department,Asset.department).join(AssetCategory,Asset.category_id==AssetCategory.id).where(Asset.id==asset_id,allowed)
    row=session.execute(statement).mappings().one_or_none()
    return AssetDetail(**row) if row is not None else None

def ticket_query(scope, *, department_id=None, status=None, priority=None):
    if status is not None and status not in STATUSES:raise ValueError('Unsupported status')
    if priority is not None and priority not in PRIORITIES:raise ValueError('Unsupported priority')
    reporter=aliased(User,name='reporter');assignee=aliased(User,name='assignee')
    own=MaintenanceTicket.reported_by_id==scope.user_id
    if scope.role=='super_admin':allowed=true()
    elif scope.role=='department_admin':allowed=or_(own,MaintenanceTicket.department_id==scope.department_id)
    elif scope.role=='technician':allowed=or_(own,MaintenanceTicket.assigned_to_id==scope.user_id)
    else:allowed=own
    statement=select(MaintenanceTicket.id,MaintenanceTicket.title,MaintenanceTicket.asset_id,MaintenanceTicket.department_id,
        MaintenanceTicket.reported_by_id,MaintenanceTicket.assigned_to_id,MaintenanceTicket.status,MaintenanceTicket.priority,
        MaintenanceTicket.created_at,reporter.display_name.label('reporter_name'),assignee.display_name.label('assignee_name')).join(reporter,MaintenanceTicket.reporter).outerjoin(assignee,MaintenanceTicket.assignee).where(allowed)
    if department_id is not None:statement=statement.where(MaintenanceTicket.department_id==department_id)
    if status is not None:statement=statement.where(MaintenanceTicket.status==status)
    if priority is not None:statement=statement.where(MaintenanceTicket.priority==priority)
    return statement

def ticket_rows(session, statement):
    return [TicketView(**row) for row in session.execute(statement).mappings()]

def department_tickets(session, scope, department_id, **filters):
    return ticket_rows(session,ticket_query(scope,department_id=department_id,**filters).order_by(MaintenanceTicket.created_at.desc(),MaintenanceTicket.id.desc()))

def technician_assignments(session, scope, technician_id=None, **filters):
    if scope.role=='student':raise PermissionError('Assignment lists require technician or administrator access')
    if scope.role=='technician':
        if technician_id is not None and technician_id!=scope.user_id:raise PermissionError('Cannot inspect another technician assignment list')
        technician_id=scope.user_id
    if technician_id is None:raise ValueError('An administrator must choose a technician')
    query=ticket_query(scope,**filters).where(MaintenanceTicket.assigned_to_id==technician_id)
    return ticket_rows(session,query.order_by(MaintenanceTicket.created_at.desc(),MaintenanceTicket.id.desc()))
