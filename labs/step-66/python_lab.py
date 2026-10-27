from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import select
from college_maintenance.models import MaintenanceTicket
from college_maintenance.search import search_tickets_query
from college_maintenance.reads import scope_for_actor
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed,client,headers
from labs.shared.performance_lab import explain,nodes,save_plans

def scenario(lab):
    ids=seed(lab)
    with lab.session() as s,s.begin():
        for title,other in [('Projector overheating',False),('Projectors overheating',False),('Projector overheating',True)]:
            s.add(MaintenanceTicket(asset_id=ids['other_asset' if other else 'asset'],department_id=ids['other_dept' if other else 'dept'],reported_by_id=ids['other' if other else 'reporter'],title=title,description='Synthetic issue',priority='low'))
    with lab.engine.begin() as c:
        check(c.exec_driver_sql("SELECT to_tsvector('english','overheats') <> to_tsvector('english','overheating')").scalar_one(),'Actual English dictionary output is tested: apparently related words need not share a stem.')
        c.exec_driver_sql(f"INSERT INTO {lab.schema}.maintenance_tickets(asset_id,department_id,reported_by_id,title,description,priority) SELECT %s,%s,%s,'Routine service','Synthetic bus fixture','low' FROM generate_series(1,20000)",(ids['asset'],ids['dept'],ids['reporter']))
        expression="to_tsvector('english'::regconfig,coalesce(title,'') || ' ' || coalesce(description,''))"
        c.exec_driver_sql(f'CREATE INDEX ticket_search_gin ON {lab.schema}.maintenance_tickets USING gin(({expression}))')
        c.exec_driver_sql(f'ANALYZE {lab.schema}.maintenance_tickets')
        plan=explain(c,f"SELECT id FROM {lab.schema}.maintenance_tickets WHERE {expression} @@ plainto_tsquery('english',%s)",('projector overheated',))
        check(any(n.get('Index Name')=='ticket_search_gin' for n in nodes(plan['Plan'])),'Selective language-matched full-text expression uses the measured GIN index.')
        save_plans(66,ranked_search=plan)
        c.exec_driver_sql(f"DELETE FROM {lab.schema}.maintenance_tickets WHERE title='Routine service'")
    with lab.session() as s:
        rows=s.execute(search_tickets_query(scope_for_actor(s,ids['admin']),'projector overheated')).all()
        check(len(rows)==2 and all(row.rank>0 for row in rows),'English stemming matches singular/plural projector and overheating forms within authorized scope.')
        check(len(s.scalars(select(MaintenanceTicket.id).where(MaintenanceTicket.title.ilike('%overheated%'))).all())==0,'Literal substring matching answers a different question from lexeme stemming.')
        check(s.execute(search_tickets_query(scope_for_actor(s,ids['admin']),'the and')).all()==[],'A stopword-only query produces no matches rather than an unrestricted list.')
    with client(lab,ids) as api:
        result=api.get('/tickets/search',params={'q':'projector overheated'},headers=headers('other_admin'))
        check(result.status_code==200 and len(result.json())==1,'The search HTTP route precedes the UUID detail route and preserves other-department isolation.')
        check(api.get('/tickets/search',params={'q':' '},headers=headers('admin')).status_code==400,'Blank search input is rejected at the established use-case validation boundary.')
    check(lab.driver().execute(f'SELECT count(*) FROM {lab.schema}.maintenance_tickets').fetchone()[0]==3,'Independent SQL confirms only the three meaningful search fixtures remain.')

if __name__=='__main__':run(66,scenario)
