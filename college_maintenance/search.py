"""Bound, language-explicit full-text search retaining ordinary ticket visibility."""
from sqlalchemy import func,literal_column
from college_maintenance.models import MaintenanceTicket
from college_maintenance.reads import ticket_query

def ticket_document():
    return func.to_tsvector(literal_column("'english'::regconfig"),
        func.coalesce(MaintenanceTicket.title,literal_column("''"))+literal_column("' '")+
        func.coalesce(MaintenanceTicket.description,literal_column("''")))

def search_tickets_query(scope,query,limit=20):
    if not isinstance(query,str) or not query.strip() or len(query)>200 or not 1<=limit<=100:raise ValueError('Invalid search input')
    term=func.plainto_tsquery(literal_column("'english'::regconfig"),query.strip())
    document=ticket_document();rank=func.ts_rank_cd(document,term)
    return ticket_query(scope).add_columns(rank.label('rank')).where(document.op('@@')(term)).order_by(rank.desc(),MaintenanceTicket.id).limit(limit)
