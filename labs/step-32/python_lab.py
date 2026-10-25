"""Compare loaders using fresh identity maps and inspect response construction."""
import importlib.util
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sqlalchemy import select, text
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import joinedload, load_only, raiseload, defer
from college_maintenance.loading import ticket_page, comment_page
from college_maintenance.models import MaintenanceTicket
from college_maintenance.reads import scope_for_actor
from labs.shared.orm_lab import check, run

spec = importlib.util.spec_from_file_location('loader_fixture', Path(__file__).parents[1]/'step-31/python_lab.py')
fixture_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(fixture_module)

def scenario(lab):
    ids, ticket_ids = fixture_module.fixture(lab)
    with lab.session() as session:
        scope = scope_for_actor(session, ids['reporter']); lab.statements.clear()
        payload = ticket_page(session, scope)
        check(len(lab.statements) == 2, 'Select-in loading serializes the three-ticket fixture with exactly two SELECTs.')
        check(sorted(len(t.comments) for t in payload) == [0,2,2], 'Optimization preserves empty and populated collections.')
        check(not any('password_hash' in sql for kind, sql in lab.statements), 'Projected loader SQL excludes user secrets.')
    check(sum(len(t.comments) for t in payload) == 4, 'The complete frozen response survives Session disposal without I/O.')
    joined = select(MaintenanceTicket).options(joinedload(MaintenanceTicket.comments))
    with lab.session() as session:
        try: session.scalars(joined).all()
        except InvalidRequestError: check(True, 'Joined collection eager loading requires explicit unique().')
        else: raise AssertionError('unique() requirement lost')
    with lab.session() as session:
        lab.statements.clear()
        rows = session.scalars(joined).unique().all()
        check(len(rows) == 3 and len(lab.statements) == 1, 'Joined loading returns three unique parents in one SELECT.')
        count = session.scalar(text(f'SELECT count(*) FROM {lab.schema}.maintenance_tickets t LEFT JOIN {lab.schema}.ticket_comments c ON c.ticket_id=t.id'))
        check(count == 5, 'The underlying join multiplies populated parents into five SQL rows.')
    with lab.session() as session:
        ticket = session.scalars(select(MaintenanceTicket).options(raiseload('*'), load_only(MaintenanceTicket.id, raiseload=True))).first()
        for name in ('comments', 'description'):
            try: getattr(ticket, name)
            except InvalidRequestError: check(True, f'Accidental unloaded {name} access raises before sending SQL.')
            else: raise AssertionError('Unloaded access succeeded')
    with lab.session() as session:
        ticket = session.scalars(select(MaintenanceTicket).options(defer(MaintenanceTicket.description, raiseload=True))).first()
        try: _ = ticket.description
        except InvalidRequestError: check(True, 'Explicit defer can independently forbid accidental large-column access.')
        else: raise AssertionError('Deferred column loaded')
        scope = scope_for_actor(session, ids['reporter'])
        first = comment_page(session, scope, ticket_ids[0], limit=1)
        second = comment_page(session, scope, ticket_ids[0], limit=1, offset=1)
        check(len(first) == len(second) == 1 and first[0]['id'] != second[0]['id'], 'Explicit collection pagination bounds child rows independently of parent pages.')
        other_scope = scope_for_actor(session, ids['other'])
        check(not comment_page(session, other_scope, ticket_ids[0]), 'Collection pagination reapplies ticket authorization.')

if __name__ == '__main__': run(32, scenario)
