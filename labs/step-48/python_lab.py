"""ORM stale-row protection and deliberate Core expected-version predicates."""
from pathlib import Path
import sys
from uuid import UUID
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import select,update,func
from sqlalchemy.orm.exc import StaleDataError
from college_maintenance.database import engine
from college_maintenance.migrations import upgrade
from college_maintenance.models import MaintenanceTicket,AuditEvent
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed,client,headers,report
from labs.shared.concurrency_lab import independent_factory

def scenario(lab):
    ids=seed(lab)
    with client(lab,ids) as api:key=UUID(report(api,ids).json()['id'])
    with independent_factory(lab) as factory:
        with factory() as first,factory() as second:
            a=first.get(MaintenanceTicket,key);b=second.get(MaintenanceTicket,key)
            check(a.version==b.version==1,'Two independent Sessions begin with the same ticket revision.')
            a.priority='critical';first.commit()
            check(a.version==2,'A normal ORM flush advances the version counter.')
            b.priority='low'
            try:second.commit()
            except StaleDataError:second.rollback();check(True,'A stale ORM edit matches zero versioned rows and raises StaleDataError.')
            else:raise AssertionError('Stale ORM write succeeded')
    with lab.session() as s:
        original=s.get(MaintenanceTicket,key)
        check(original.priority=='critical' and original.version==2,'The winning administrator-style edit remains intact after stale rollback.')
    # Roll this bypass experiment back: bulk/Core DML is not mapper versioning.
    with lab.session() as s:
        row=s.execute(update(MaintenanceTicket).where(MaintenanceTicket.id==key).values(priority='low').returning(MaintenanceTicket.version)).one()
        check(row.version==2,'Unqualified Core/bulk DML bypasses automatic mapper version increment.')
        s.rollback()
        matched=s.execute(update(MaintenanceTicket).where(MaintenanceTicket.id==key,MaintenanceTicket.version==1)
            .values(priority='low',version=MaintenanceTicket.version+1).returning(MaintenanceTicket.id)).one_or_none()
        check(matched is None,'A deliberate expected-version predicate rejects stale Core DML too.')
        s.rollback()
    with client(lab,ids) as api:
        current=api.get(f'/tickets/{key}',headers=headers('admin')).json()
        check(current['version']==2,'The detail response supplies the version needed for a protected client edit.')
        accepted=api.patch(f'/tickets/{key}/priority',headers=headers('admin'),json={'priority':'high','expected_version':2})
        check(accepted.status_code==200 and accepted.json()['version']==3,'An authorized edit with the current expected version succeeds and returns the next version.')
        rejected=api.patch(f'/tickets/{key}/priority',headers=headers('admin'),json={'priority':'low','expected_version':2})
        check(rejected.status_code==409,'A stale direct API request receives a conflict instead of overwriting the winning edit.')
        check(api.patch(f'/tickets/{key}/priority',headers=headers('admin'),json={'priority':'low'}).status_code==422,'Protected edits require a caller-provided expected version.')
    with lab.session() as s:
        check(s.get(MaintenanceTicket,key).priority=='high' and s.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action=='ticket_priority_changed'))==1,'Rejected stale edits create neither a changed value nor a success audit event.')
    with engine.begin() as connection:upgrade(connection)

if __name__=='__main__':run(48,scenario)
