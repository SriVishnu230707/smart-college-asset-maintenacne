"""Compare SQL shapes, cardinality, deterministic ties and complete migrations."""
from datetime import datetime,timedelta,timezone
from pathlib import Path
from uuid import UUID
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import select,func,inspect,CheckConstraint,text
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from college_maintenance.advanced_reports import latest_comments_query,repair_costs_cte
from college_maintenance.database import engine
from college_maintenance.migrations import upgrade
from college_maintenance.models import Base,MaintenanceTicket,TicketComment
from college_maintenance.reads import scope_for_actor
from college_maintenance.reports import report_scope
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed,client,headers
from labs.shared.migration_lab import temporary_database

def names_match(connection):
    catalog=inspect(connection)
    return all({str(c.name) for c in table.constraints if isinstance(c,CheckConstraint)} ==
        {row['name'] for row in catalog.get_check_constraints(table.name)} for table in Base.metadata.sorted_tables)

def scenario(lab):
    ids=seed(lab);base=datetime(2026,10,25,tzinfo=timezone.utc)
    with lab.session() as s,s.begin():
        for number in range(1,5):
            other=number==4
            s.add(MaintenanceTicket(id=UUID(int=number),asset_id=ids['other_asset' if other else 'asset'],
                department_id=ids['other_dept' if other else 'dept'],reported_by_id=ids['other' if other else 'reporter'],
                title=f'Query {number}',description='Synthetic report fixture',priority='high' if number in (1,3) else 'low'))
        s.flush()
        for number,ticket,body,at in [(500,1,'ZZZ older',base-timedelta(days=1)),(501,1,'Lower tie',base),(502,1,'A winner',base),(503,3,'Third',base)]:
            s.add(TicketComment(id=UUID(int=number),ticket_id=UUID(int=ticket),author_id=ids['reporter'],body=body,created_at=at))
    with lab.session() as s:
        scope=scope_for_actor(s,ids['admin']);results=[]
        for strategy in ('lateral','distinct_on','scalar'):
            lab.statements.clear();rows=[dict(row) for row in s.execute(latest_comments_query(scope,strategy)).mappings()];results.append(rows)
            check(len(lab.statements)==1 and len(rows)==3,f'{strategy} sends one SELECT and returns one row per authorized ticket.')
        check(results[0]==results[1]==results[2],'LATERAL, DISTINCT ON CTE, and correlated scalar formulations return identical projected values.')
        check(results[0][0]['comment_id']==UUID(int=502) and results[0][0]['latest_body']=='A winner','Equal comment timestamps use descending UUID as the deterministic latest-row tie-breaker.')
        check(results[0][1]['comment_id'] is None and results[0][1]['latest_body'] is None,'A ticket without comments remains present with NULL child values.')
        check(s.scalar(select(func.max(TicketComment.body)).where(TicketComment.ticket_id==UUID(int=1)))!='A winner','MAX(body) is a lexical aggregate and does not answer latest-comment selection.')
        allowed=report_scope(scope,MaintenanceTicket.department_id)
        all_ids=select(MaintenanceTicket.id).where(allowed)
        high=all_ids.where(MaintenanceTicket.priority=='high')
        check(len(s.scalars(all_ids.union(high)).all())==3 and len(s.scalars(all_ids.union_all(high)).all())==5,'UNION deduplicates ticket identities while UNION ALL intentionally retains multiplicity.')
        commented=all_ids.where(MaintenanceTicket.id.in_(select(TicketComment.ticket_id)))
        missing=s.scalars(all_ids.except_(commented)).all()
        not_exists=s.scalars(all_ids.where(~select(TicketComment.id).where(TicketComment.ticket_id==MaintenanceTicket.id).exists())).all()
        check(missing==not_exists==[UUID(int=2)],'EXCEPT and correlated NOT EXISTS agree on the ticket with no comments without a nullable NOT IN trap.')
        check(set(s.scalars(all_ids.intersect(high)))=={UUID(int=1),UUID(int=3)},'INTERSECT preserves the intended ticket-identity grain.')
        costs=repair_costs_cte()
        check(s.scalar(select(func.coalesce(func.sum(costs.c.total_cost),0)))==0,'The reusable completed-order CTE composes into an aggregate with explicit empty-input behavior.')
        try:latest_comments_query(scope,'unreviewed')
        except ValueError:check(True,'Only reviewed query strategies are accepted.')
        else:raise AssertionError('Unknown strategy accepted')
        copied=results[0]
    check(copied[0]['latest_body']=='A winner','Projected latest-comment data remains usable after Session cleanup.')
    observer=lab.driver()
    raw=observer.execute(f'''SELECT t.id,t.title,c.id,c.body FROM {lab.schema}.maintenance_tickets t
        LEFT JOIN LATERAL (SELECT id,body FROM {lab.schema}.ticket_comments c WHERE c.ticket_id=t.id ORDER BY created_at DESC,id DESC LIMIT 1) c ON true
        WHERE t.department_id=%s ORDER BY t.id''',(ids['dept'],)).fetchall()
    check(raw==[tuple(row.values()) for row in copied],'Independent hand-written LATERAL SQL agrees with all SQLAlchemy projected rows.')
    with client(lab,ids) as api:
        check(len(api.get('/reports/latest-comments',headers=headers('admin')).json())==3,'The latest-comment HTTP report enforces administrator department scope.')
        other=api.get('/reports/latest-comments',headers=headers('other_admin')).json()
        check(len(other)==1 and other[0]['latest_body'] is None,'Other-department administration sees only its own empty-comment ticket.')
        check(api.get('/reports/latest-comments',headers=headers('reporter')).status_code==403,'Reporter access does not grant administrative report access.')
    with engine.begin() as connection:upgrade(connection)
    with engine.connect() as connection:
        check(not compare_metadata(MigrationContext.configure(connection,opts={'compare_type':True,'compare_server_default':True}),Base.metadata),'The complete application model has no migration autogenerate drift.')
        check(names_match(connection),'Exact catalog CHECK names match ORM metadata, including names autogenerate does not compare.')
        check(connection.scalar(text('SELECT version_num FROM alembic_version'))=='0012_names','The forward naming correction is recorded as the reviewed migration head.')
    with temporary_database(26,lab.run_id) as fresh:
        with fresh.begin() as connection:
            upgrade(connection,'0008_attachments')
            connection.execute(text("INSERT INTO spare_parts(sku,display_name,current_unit_cost,stock_quantity) VALUES ('LEGACY','Legacy stock',5.00,3)"))
            upgrade(connection)
            check(connection.execute(text('SELECT quantity_delta,is_legacy,actor_id FROM inventory_movements')).one()==(3,True,None),'The migration chain adopts a populated pre-ledger balance without inventing a human actor.')
            check(names_match(connection) and not compare_metadata(MigrationContext.configure(connection,opts={'compare_type':True,'compare_server_default':True}),Base.metadata),'A fresh database upgraded through every revision has exact CHECK names and no model drift.')

if __name__=='__main__':run(50,scenario)
