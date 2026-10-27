"""Scoped window reports with explicit tie and frame policies."""
from sqlalchemy import func, select
from college_maintenance.reports import failure_frequency_query


def ranked_failures_query(scope, *, top=3, include_ties=True):
    if not 1 <= top <= 100:
        raise ValueError('top must be between 1 and 100')
    counts = failure_frequency_query(scope).order_by(None).subquery('failure_counts')
    ranking = (func.dense_rank().over(partition_by=counts.c.department_id,
               order_by=counts.c.ticket_count.desc()) if include_ties else
               func.row_number().over(partition_by=counts.c.department_id,
               order_by=(counts.c.ticket_count.desc(), counts.c.asset_id)))
    ranked = select(counts, ranking.label('position')).subquery('ranked_failures')
    return select(ranked).where(ranked.c.position <= top).order_by(
        ranked.c.department_id, ranked.c.position, ranked.c.asset_id)
