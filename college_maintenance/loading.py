"""Explicit loader examples and a separately paginated comment collection."""
from dataclasses import dataclass
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import load_only, raiseload, selectinload
from college_maintenance.models import MaintenanceTicket, TicketComment
from college_maintenance.reads import ticket_query

@dataclass(frozen=True)
class CommentedTicket:
    id: UUID
    title: str
    comments: tuple[str, ...]

def ticket_page(session, scope, limit=20):
    """Two SELECTs for this small page; use comment_page for large collections."""
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('limit must be 1-100')
    allowed = ticket_query(scope).with_only_columns(MaintenanceTicket.id)
    statement = (select(MaintenanceTicket).where(MaintenanceTicket.id.in_(allowed))
        .order_by(MaintenanceTicket.created_at.desc(), MaintenanceTicket.id.desc()).limit(limit)
        .options(load_only(MaintenanceTicket.id, MaintenanceTicket.title, raiseload=True),
                 selectinload(MaintenanceTicket.comments).load_only(TicketComment.id, TicketComment.body, raiseload=True), raiseload('*')))
    return tuple(CommentedTicket(t.id, t.title, tuple(c.body for c in t.comments)) for t in session.scalars(statement))

def comment_page(session, scope, ticket_id, limit=20, offset=0):
    if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or not 0 <= offset <= 100000:
        raise ValueError('Invalid collection pagination')
    allowed = ticket_query(scope).with_only_columns(MaintenanceTicket.id)
    return tuple(session.execute(select(TicketComment.id, TicketComment.body, TicketComment.author_id, TicketComment.created_at)
        .where(TicketComment.ticket_id == ticket_id, TicketComment.ticket_id.in_(allowed))
        .order_by(TicketComment.created_at, TicketComment.id).offset(offset).limit(limit)).mappings())
