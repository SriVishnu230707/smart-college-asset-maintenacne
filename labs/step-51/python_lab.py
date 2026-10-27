"""Hand-counted ranks, ties, frames, and lag against real PostgreSQL."""
from pathlib import Path
from uuid import UUID
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import select,text
from college_maintenance.analytics import ranked_failures_query
from college_maintenance.models import Asset,MaintenanceTicket
from college_maintenance.reads import scope_for_actor
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed

def scenario(lab):
    ids=seed(lab)
    with lab.session() as s,s.begin():
        for number,count in [(1,3),(2,3),(3,1)]:
            asset=Asset(id=UUID(int=100+number),asset_code=f'RANK-{number}',name='Rank asset',department_id=ids['dept'],category_id=ids['category'])
            s.add(asset);s.flush()
            for j in range(count):s.add(MaintenanceTicket(asset_id=asset.id,department_id=ids['dept'],reported_by_id=ids['reporter'],title='Synthetic failure',description='Rank fixture',priority='low'))
    with lab.session() as s:
        scope=scope_for_actor(s,ids['admin'])
        rows=s.execute(ranked_failures_query(scope,top=1)).all()
        check(len(rows)==2 and all(r.position==1 and r.ticket_count==3 for r in rows),'Dense ranking retains both highest-count ties.')
        rows=s.execute(ranked_failures_query(scope,top=1,include_ties=False)).all()
        check(len(rows)==1 and rows[0].asset_id==UUID(int=101),'Row numbering uses asset UUID to deterministically break ties.')
        check([r.position for r in s.execute(ranked_failures_query(scope,top=2))]==[1,1,2],'Ranking is applied after reducing reports to asset grain.')
        check(s.execute(ranked_failures_query(scope_for_actor(s,ids['other_admin']))).all()==[],'Ranking preserves department scope.')
        try:ranked_failures_query(scope,top=0)
        except ValueError:check(True,'Invalid ranking limits are rejected.')
        else:raise AssertionError('Unbounded rank accepted')
        raw=s.execute(text('''WITH v(id,k,n) AS (VALUES (1,1,10),(2,1,20),(3,2,5))
            SELECT id,sum(n) OVER(ORDER BY k) AS peers,
            sum(n) OVER(ORDER BY k,id ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running,
            lag(n) OVER(ORDER BY id) AS previous FROM v ORDER BY id''')).all()
        check(raw==[(1,30,10,None),(2,30,30,10),(3,35,35,20)],'Peer RANGE totals differ from explicitly ordered ROWS frames; lag retains the first NULL.')
    observer=lab.driver()
    counts=observer.execute(f'SELECT count(*) FROM {lab.schema}.maintenance_tickets').fetchone()[0]
    check(counts==7,'An independent connection observes all seven committed synthetic reports.')

if __name__=='__main__':run(51,scenario)
