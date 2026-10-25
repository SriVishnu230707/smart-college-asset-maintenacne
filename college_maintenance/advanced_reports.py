"""Equivalent latest-child queries with explicit grain, tie and NULL policies."""
from sqlalchemy import select,true
from sqlalchemy.dialects.postgresql import distinct_on
from college_maintenance.models import MaintenanceTicket,TicketComment
from college_maintenance.reports import report_scope,completed_order_costs

def latest_comment_cte():
    return (select(TicketComment.ticket_id,TicketComment.id.label('comment_id'),TicketComment.body.label('latest_body'))
        .ext(distinct_on(TicketComment.ticket_id))
        .order_by(TicketComment.ticket_id,TicketComment.created_at.desc(),TicketComment.id.desc()).cte('latest_comments'))

def latest_comments_query(scope,strategy='lateral'):
    allowed=report_scope(scope,MaintenanceTicket.department_id)
    base=select(MaintenanceTicket.id.label('ticket_id'),MaintenanceTicket.title)
    latest=(select(TicketComment.id.label('comment_id'),TicketComment.body.label('latest_body'))
        .where(TicketComment.ticket_id==MaintenanceTicket.id)
        .order_by(TicketComment.created_at.desc(),TicketComment.id.desc()).limit(1).correlate(MaintenanceTicket))
    if strategy=='lateral':
        child=latest.lateral('latest_comment')
        query=base.add_columns(child.c.comment_id,child.c.latest_body).outerjoin(child,true())
    elif strategy=='distinct_on':
        child=latest_comment_cte()
        query=base.add_columns(child.c.comment_id,child.c.latest_body).outerjoin(child,child.c.ticket_id==MaintenanceTicket.id)
    elif strategy=='scalar':
        query=base.add_columns(latest.with_only_columns(TicketComment.id).scalar_subquery().label('comment_id'),
            latest.with_only_columns(TicketComment.body).scalar_subquery().label('latest_body'))
    else:raise ValueError('Unknown latest-comment strategy')
    return query.where(allowed).order_by(MaintenanceTicket.id)

def repair_costs_cte():
    """Reusable one-row-per-completed-order expression from Step 49."""
    return completed_order_costs().cte('repair_costs')
