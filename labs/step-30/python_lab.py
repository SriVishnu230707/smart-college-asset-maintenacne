"""Page tied timestamps, compare offset drift, and expose cross-request limits."""
import sys
import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import text
from college_maintenance.database import engine
from college_maintenance.migrations import upgrade
from college_maintenance.models import Base, MaintenanceTicket
from college_maintenance.pagination import ticket_feed, offset_feed
from college_maintenance.reads import scope_for_actor
from labs.shared.orm_lab import check,run

def scenario(lab):
    ids=lab.seed();base=datetime(2026,10,25,tzinfo=timezone.utc)
    with lab.session() as s,s.begin():
        s.add_all([MaintenanceTicket(id=UUID(int=i),asset_id=ids['asset'],reported_by_id=ids['reporter'],department_id=ids['dept'],
            title=f'T-{i}',description='Paging fixture',priority='high' if i%2==0 else 'low',created_at=base+timedelta(minutes=i//5)) for i in range(1,9)])
    with lab.session() as s:
        scope=scope_for_actor(s,ids['reporter']);cursor=None;seen=[]
        for _ in range(10):
            page=ticket_feed(s,scope,limit=3,cursor=cursor)
            seen.extend(r.id.int for r in page.items)
            if page.next_cursor is None:break
            cursor=page.next_cursor
        check(seen==[8,7,6,5,4,3,2,1] and len(seen)==len(set(seen)),'Compound created_at/id cursors page tied timestamps exactly once in the fixed dataset.')
        check(ticket_feed(s,scope,limit=100).next_cursor is None,'The final page has no continuation token.')
        check(not ticket_feed(s,scope,department_id=ids['other_dept']).items,'A filter with no authorized rows returns an empty page.')
        filtered=ticket_feed(s,scope,limit=2,priority='high');tail=ticket_feed(s,scope,limit=2,priority='high',cursor=filtered.next_cursor)
        check([r.id.int for r in filtered.items+tail.items]==[8,6,4,2],'Priority-filtered keyset traversal preserves ordering and completeness.')
        first=ticket_feed(s,scope,limit=2);original_ids={r.id for r in first.items};saved_cursor=first.next_cursor
        malformed=json.loads(base64.urlsafe_b64decode(saved_cursor+'='*(-len(saved_cursor)%4)))
        malformed['id']=7
        wrong_type=base64.urlsafe_b64encode(json.dumps(malformed).encode()).decode()
        invalid_calls=[dict(limit=0),dict(limit=True),dict(limit=101),dict(sort='arbitrary'),dict(cursor='not-base64!'),dict(cursor=wrong_type),dict(cursor=saved_cursor,priority='low')]
        for kwargs in invalid_calls:
            try:ticket_feed(s,scope,**kwargs)
            except ValueError:pass
            else:raise AssertionError(f'Invalid pagination input accepted: {kwargs}')
        check(True,'Limits, sort names, malformed tokens, and changed cursor filters are rejected.')
        other_scope=scope_for_actor(s,ids['tech'])
        try:ticket_feed(s,other_scope,cursor=saved_cursor)
        except ValueError:check(True,'A cursor from another actor scope cannot be reused.')
        else:raise AssertionError('Cross-actor cursor accepted')
        try:offset_feed(s,scope,offset=-1)
        except ValueError:check(True,'Negative offsets are rejected before executing SQL.')
        else:raise AssertionError('Negative offset accepted')
    driver=lab.driver()
    def insert_extra(number,instant):
        driver.execute(f'''INSERT INTO {lab.schema}.maintenance_tickets
            (id,asset_id,reported_by_id,department_id,title,description,priority,created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)''',(UUID(int=number),ids['asset'],ids['reporter'],ids['dept'],f'EXTRA-{number}','Concurrent fixture','high',instant))
    insert_extra(99,base+timedelta(minutes=2))
    with lab.session() as s:
        scope=scope_for_actor(s,ids['reporter'])
        shifted=offset_feed(s,scope,offset=2,limit=2)
        continued=ticket_feed(s,scope,limit=2,cursor=saved_cursor)
        check(bool(original_ids.intersection(r.id for r in shifted)),'An insert ahead of the offset causes a repeated row on the next offset page.')
        check(not original_ids.intersection(r.id for r in continued.items),'The same newer insert does not repeat boundary rows in keyset continuation.')
        check(all(r.id.int!=99 for r in continued.items),'Newer rows above the cursor require a feed restart to appear.')
    insert_extra(77,base-timedelta(minutes=1))
    with lab.session() as s:
        scope=scope_for_actor(s,ids['reporter'])
        check(any(r.id.int==77 for r in ticket_feed(s,scope,limit=100,cursor=saved_cursor).items),
              'A backdated insert below the cursor can enter later pages; separate requests are not one snapshot.')
    driver.execute(f'UPDATE {lab.schema}.maintenance_tickets SET created_at=%s WHERE id=%s',(base-timedelta(minutes=5),UUID(int=8)))
    with lab.session() as s:
        scope=scope_for_actor(s,ids['reporter'])
        check(any(r.id.int==8 for r in ticket_feed(s,scope,limit=100,cursor=saved_cursor).items),
              'Changing an ordering timestamp can repeat a previously seen row, documenting the immutable-order-key requirement.')
    with engine.begin() as c:
        upgrade(c)
        changes=compare_metadata(MigrationContext.configure(c,opts={'compare_type':True,'compare_server_default':True}),Base.metadata)
        check(not changes,'The migration head and complete application metadata have no autogenerate drift.')
        check(c.scalar(text("SELECT count(*) FROM pg_indexes WHERE schemaname='public' AND indexname='ix_maintenance_tickets_created_at_id'"))==1,
              'The compound feed index is installed by the reviewed migration.')

if __name__=='__main__':run(30,scenario)
