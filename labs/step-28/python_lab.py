"""One owner commits all writes and audit; helpers never commit independently."""
import sys
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from college_maintenance.database import engine
from college_maintenance.migrations import upgrade
from college_maintenance.models import Asset, AuditEvent, Department, MaintenanceTicket
from college_maintenance.persistence import add_asset_row, add_ticket_row, add_audit_row, record_asset_report, unit_of_work
from labs.shared.orm_lab import check,run

def scenario(lab):
    ids=lab.seed();commits=[]
    def factory():
        s=lab.session();event.listen(s,'after_commit',lambda session:commits.append(True));return s
    result=record_asset_report(actor_id=ids['reporter'],department_id=ids['dept'],category_id=ids['category'],
        code='ATOMIC-OK',name='Atomic asset',title='Atomic report',session_factory=factory)
    check(len(commits)==1,'The use-case boundary commits exactly once for asset, ticket, and audit together.')
    with lab.session() as s:
        check(s.get(Asset,result['asset_id']).asset_code=='ATOMIC-OK' and s.get(MaintenanceTicket,result['ticket_id']).reported_by_id==ids['reporter'],
              'The successful use case persists both writes and derives the ticket reporter from the actor.')
        check(s.get(AuditEvent,result['audit_id']).ticket_id==result['ticket_id'],'The successful audit event references the same committed changes.')
    try:
        with lab.session() as s,unit_of_work(s):
            a=add_asset_row(s,code='ATOMIC-ABORT',name='Aborted asset',department_id=ids['dept'],category_id=ids['category'])
            t=add_ticket_row(s,asset=a,actor_id=ids['reporter'],title='Abort report')
            add_audit_row(s,actor_id=ids['reporter'],asset=a,ticket=t)
            check(s.in_transaction(),'All three helper flushes remain inside the owner transaction.')
            raise RuntimeError('Injected use-case failure')
    except RuntimeError as exc:check(str(exc)=='Injected use-case failure','An error after all helper writes escapes the owner and triggers rollback.')
    with lab.session() as s:
        check(s.scalar(select(Asset.id).where(Asset.asset_code=='ATOMIC-ABORT')) is None
              and len(s.scalars(select(AuditEvent)).all())==1,'No aborted asset, ticket, or success audit can commit independently.')
    try:
        with lab.session() as s,unit_of_work(s):
            a=add_asset_row(s,code='BAD-AUDIT',name='Invalid audit asset',department_id=ids['dept'],category_id=ids['category'])
            t=add_ticket_row(s,asset=a,actor_id=ids['reporter'],title='Invalid audit report')
            add_audit_row(s,actor_id=uuid4(),asset=a,ticket=t)
    except IntegrityError as exc:check(exc.orig.sqlstate=='23503','A failed final audit reference rolls back both preceding successful writes.')
    else:raise AssertionError('Invalid audit reference accepted')
    with lab.session() as s:
        check(s.scalar(select(Asset.id).where(Asset.asset_code=='BAD-AUDIT')) is None,'The failed audit leaves no partially committed asset.')
    with lab.session() as s:
        s.get(Department,ids['dept'])
        try:
            with unit_of_work(s):pass
        except InvalidRequestError:check(s.in_transaction(),'An earlier read is not silently committed or rolled back by a second transaction owner.')
        else:raise AssertionError('A second owner accepted an active transaction')
        s.rollback()
        with unit_of_work(s):check(s.get(Asset,ids['asset']) is not None,'Explicitly resolving the earlier read permits a new clear transaction boundary.')
    with engine.begin() as c:upgrade(c)
    check(True,'The audit table is installed by its own reviewed Alembic revision.')

if __name__=='__main__':run(28,scenario)
