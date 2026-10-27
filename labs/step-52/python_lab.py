from pathlib import Path
from datetime import date,datetime,timezone
from decimal import Decimal
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import text
from college_maintenance.analytics import monthly_costs_query
from college_maintenance.models import MaintenanceTicket,WorkOrder
from college_maintenance.reads import scope_for_actor
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed

def scenario(lab):
    ids=seed(lab)
    with lab.session() as s,s.begin():
        ticket=MaintenanceTicket(asset_id=ids['asset'],department_id=ids['dept'],reported_by_id=ids['reporter'],title='Boundary report',description='Synthetic event',priority='low')
        s.add(ticket);s.flush()
        for instant,cost in [('2026-01-31T18:29:59+00:00','10.00'),('2026-01-31T18:30:00+00:00','20.00'),('2026-03-01T00:00:00+00:00','0.00')]:
            s.add(WorkOrder(ticket_id=ticket.id,technician_id=ids['tech'],status='completed',labor_cost=Decimal(cost),completed_at=datetime.fromisoformat(instant)))
    with lab.session() as s:
        scope=scope_for_actor(s,ids['admin'])
        rows=s.execute(monthly_costs_query(scope,date(2026,1,1),date(2026,5,1))).all()
        check([r.cost for r in rows]==[10,20,0,0],'Local month grid includes both zero-cost and missing months.')
        check([r.change for r in rows]==[None,10,-20,0],'lag runs after zero-filled month aggregation.')
        utc=s.execute(monthly_costs_query(scope,date(2026,1,1),date(2026,3,1),'UTC')).all()
        check([r.cost for r in utc]==[30,0],'UTC and Kolkata month boundaries deliberately attribute the same instants differently.')
        check(len(s.execute(monthly_costs_query(scope_for_actor(s,ids['super']),date(2026,1,1),date(2026,5,1))).all())==8,'Empty departments retain one row per requested month.')
        for start,end,zone in [(date(2026,1,2),date(2026,2,1),'UTC'),(date(2026,1,1),date(2026,2,1),'untrusted')]:
            try:monthly_costs_query(scope,start,end,zone)
            except ValueError:check(True,'Invalid range or timezone is rejected before querying.')
            else:raise AssertionError('Invalid reporting input')
        result=s.execute(text("SELECT extract(epoch FROM (timestamptz '2026-02-01 01:00+00'-timestamptz '2026-02-01 00:00+00')), NULL::timestamptz-timestamptz '2026-02-01 00:00+00'")).one()
        check(result==(Decimal(3600),None),'Elapsed seconds preserve NULL for unfinished work; duration policy is per completed order, not guessed from ticket closure.')
    check(lab.driver().execute(f'SELECT sum(labor_cost) FROM {lab.schema}.work_orders').fetchone()[0]==30,'Independent SQL verifies the exact completed labor total.')

if __name__=='__main__':run(52,scenario)
