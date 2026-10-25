"""Measure the exact lazy accesses, retaining an intentionally unoptimized baseline."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sqlalchemy import select
from sqlalchemy.orm.exc import DetachedInstanceError
from college_maintenance.database import engine
from college_maintenance.migrations import upgrade
from college_maintenance.models import MaintenanceTicket, TicketComment
from labs.shared.orm_lab import check, run

def fixture(lab):
    ids = lab.seed()
    with lab.session() as session, session.begin():
        tickets = [MaintenanceTicket(asset_id=ids['asset'], department_id=ids['dept'], reported_by_id=ids['reporter'],
            title=f'Loader {i}', description='Synthetic loader fixture', priority='high') for i in range(3)]
        session.add_all(tickets); session.flush()
        for ticket in tickets[:2]:
            session.add_all([TicketComment(ticket_id=ticket.id, author_id=ids['reporter'], body=f'Comment {i}') for i in range(2)])
        return ids, [t.id for t in tickets]

def scenario(lab):
    ids, ticket_ids = fixture(lab)
    with lab.session() as session:
        lab.statements.clear()
        tickets = session.scalars(select(MaintenanceTicket).where(MaintenanceTicket.id.in_(ticket_ids)).order_by(MaintenanceTicket.title)).all()
        check(len(lab.statements) == 1, 'Fetching three tickets initially sends exactly one SELECT.')
        payload = []
        for i, ticket in enumerate(tickets):
            payload.append(dict(id=ticket.id, comments=[c.body for c in ticket.comments]))
            check(len(lab.statements) == i+2, f'Access to ticket {i+1} comments adds one lazy SELECT, even for an empty collection.')
        check([len(p['comments']) for p in payload] == [2,2,0], 'Serialization retains all comments and the empty ticket.')
        check(sum(kind == 'SELECT' for kind, sql in lab.statements) == 4, 'The regression baseline records 1+N SELECTs for N=3.')
        before = len(lab.statements)
        _ = tickets[0].comments
        check(len(lab.statements) == before, 'Repeated access to the loaded collection uses Session state.')
    check(payload[0]['comments'] == ['Comment 0','Comment 1'] or set(payload[0]['comments']) == {'Comment 0','Comment 1'}, 'Copied primitive response values survive Session close.')
    with lab.session() as session:
        detached = session.get(MaintenanceTicket, ticket_ids[0])
    try: _ = detached.comments
    except DetachedInstanceError: check(True, 'Serializing an unloaded detached collection fails instead of secretly issuing SQL.')
    else: raise AssertionError('Detached lazy collection loaded')
    with engine.begin() as connection: upgrade(connection)

if __name__ == '__main__': run(31, scenario)
