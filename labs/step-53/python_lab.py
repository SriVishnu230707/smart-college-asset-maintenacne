from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import text
from college_maintenance.models import MaintenanceTicket,WorkOrder
from college_maintenance.report_views import install_views,remove_views
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed

def scenario(lab):
    ids=seed(lab)
    with lab.session() as s,s.begin():
        ticket=MaintenanceTicket(asset_id=ids['asset'],department_id=ids['dept'],reported_by_id=ids['reporter'],title='View fixture',description='Synthetic data',priority='low')
        s.add(ticket);s.flush();ticket_id=ticket.id
        s.add(WorkOrder(ticket_id=ticket_id,technician_id=ids['tech'],status='completed',labor_cost=5))
    try:
        with lab.engine.begin() as c:install_views(c,lab.schema)
        observer=lab.driver()
        def total(name):return observer.execute(f'SELECT sum(total_cost) FROM {lab.schema}.{name}').fetchone()[0]
        check(total('repair_cost_view')==total('department_cost_cache')==5,'Live and materialized views initially agree on exact completed cost.')
        with lab.session() as s,s.begin():s.add(WorkOrder(ticket_id=ticket_id,technician_id=ids['tech'],status='completed',labor_cost=7))
        check(total('repair_cost_view')==12 and total('department_cost_cache')==5,'A live view sees committed work immediately; its materialized counterpart is stale until refreshed.')
        with lab.engine.begin() as c:c.exec_driver_sql(f'REFRESH MATERIALIZED VIEW CONCURRENTLY {lab.schema}.department_cost_cache')
        check(total('department_cost_cache')==12,'Concurrent refresh with a qualifying unique index publishes the new total.')
        identity=observer.execute(f'SELECT count(*),count(DISTINCT work_order_id) FROM {lab.schema}.repair_cost_view').fetchone()
        check(identity==(2,2),'The live projection has a genuine unique work-order identity; no artificial ORM primary key is invented.')
        check(observer.execute(f"SELECT relkind FROM pg_class WHERE oid='{lab.schema}.department_cost_cache'::regclass").fetchone()[0]=='m','Catalog inspection distinguishes materialized storage from a view definition.')
        try:install_views(None,'public; DROP TABLE x')
        except ValueError:check(True,'Identifiers are validated separately from data parameters.')
        else:raise AssertionError('Invalid schema')
        print('Policy: optional cache refresh is explicit; scoped base reports remain authoritative and these views are not public API grants.')
    finally:
        with lab.engine.begin() as c:remove_views(c,lab.schema)
    check(lab.driver().execute("SELECT to_regclass(%s)",(lab.schema+'.repair_cost_view',)).fetchone()[0] is None,'Optional projections are removed before guarded table cleanup.')

if __name__=='__main__':run(53,scenario)
