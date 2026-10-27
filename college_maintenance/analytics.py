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


def monthly_costs_query(scope, start, end, zone='Asia/Kolkata'):
    """One department/month, start-inclusive end-exclusive; fill missing months."""
    from datetime import date
    from sqlalchemy import cast, DateTime, literal, text, true
    from college_maintenance.models import Department, WorkOrder
    from college_maintenance.reports import completed_order_costs, report_scope
    if not isinstance(start,date) or not isinstance(end,date) or start.day!=1 or end.day!=1 or not start<end:
        raise ValueError('Use increasing month-start dates')
    if (end.year-start.year)*12+end.month-start.month>120:raise ValueError('Report range exceeds 120 months')
    if zone not in {'UTC','Asia/Kolkata'}:raise ValueError('Unsupported reporting zone')
    months=select(func.generate_series(cast(literal(start),DateTime),
        cast(literal(end),DateTime)-text("interval '1 month'"),text("interval '1 month'")).label('month')).cte('months')
    costs=completed_order_costs().subquery()
    month=func.date_trunc('month',func.timezone(zone,WorkOrder.completed_at))
    totals=(select(costs.c.department_id,month.label('month'),func.sum(costs.c.total_cost).label('cost'))
        .join(WorkOrder,WorkOrder.id==costs.c.work_order_id).group_by(costs.c.department_id,month).subquery())
    grid=(select(Department.id.label('department_id'),Department.code,months.c.month,
        func.coalesce(totals.c.cost,0).label('cost')).select_from(Department).join(months,true())
        .outerjoin(totals,(totals.c.department_id==Department.id)&(totals.c.month==months.c.month))
        .where(report_scope(scope,Department.id))).cte('monthly_grid')
    return select(grid,(grid.c.cost-func.lag(grid.c.cost).over(partition_by=grid.c.department_id,
        order_by=grid.c.month)).label('change')).order_by(grid.c.department_id,grid.c.month)
