"""Explicit optional read projections; not an authorization boundary."""
import re

def install_views(connection, schema):
    if not re.fullmatch(r'college_step\d{2}',schema):raise ValueError('Study schema required')
    connection.exec_driver_sql(f'''CREATE VIEW {schema}.repair_cost_view AS
        WITH parts AS (SELECT work_order_id,sum(quantity_used*unit_cost_at_use) cost
            FROM {schema}.work_order_parts GROUP BY work_order_id)
        SELECT w.id AS work_order_id,t.department_id,w.labor_cost+coalesce(p.cost,0) AS total_cost
        FROM {schema}.work_orders w JOIN {schema}.maintenance_tickets t ON t.id=w.ticket_id
        LEFT JOIN parts p ON p.work_order_id=w.id WHERE w.status='completed' ''')
    connection.exec_driver_sql(f'CREATE MATERIALIZED VIEW {schema}.department_cost_cache AS SELECT department_id,sum(total_cost) total_cost FROM {schema}.repair_cost_view GROUP BY department_id')
    connection.exec_driver_sql(f'CREATE UNIQUE INDEX ON {schema}.department_cost_cache(department_id)')

def remove_views(connection,schema):
    if not re.fullmatch(r'college_step\d{2}',schema):raise ValueError('Study schema required')
    connection.exec_driver_sql(f'DROP MATERIALIZED VIEW IF EXISTS {schema}.department_cost_cache')
    connection.exec_driver_sql(f'DROP VIEW IF EXISTS {schema}.repair_cost_view')
