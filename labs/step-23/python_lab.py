"""Disambiguate ticket reporter/assignee navigation and projection aliases."""
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import inspect, select, text
from sqlalchemy.orm import aliased
from college_maintenance.models import MaintenanceTicket, User
from labs.shared.orm_lab import check, run

def scenario(lab):
    ids=lab.seed()
    with lab.session() as s,s.begin():
        reporter=s.get(User,ids['reporter']); tech=s.get(User,ids['tech'])
        for title,who,assignee in [('DIFFERENT',reporter,tech),('SAME',tech,tech),('UNASSIGNED',reporter,None)]:
            ticket=MaintenanceTicket(asset_id=ids['asset'],department_id=ids['dept'],title=title,
                description='Alias fixture',priority='high',reporter=who,assignee=assignee,
                status='assigned' if assignee else 'open',assigned_at=datetime.now(timezone.utc) if assignee else None)
            s.add(ticket)
        s.flush()
        check({t.title for t in reporter.reported_tickets}=={'DIFFERENT','UNASSIGNED'},'Reporter navigation follows only reported_by_id.')
        check({t.title for t in tech.assigned_tickets}=={'DIFFERENT','SAME'},'Assignee navigation follows only assigned_to_id.')
    reporter=aliased(User,name='reporter'); assignee=aliased(User,name='assignee')
    query=select(MaintenanceTicket.title,reporter.display_name.label('reporter_name'),assignee.display_name.label('assignee_name')).join(reporter,MaintenanceTicket.reporter).outerjoin(assignee,MaintenanceTicket.assignee).order_by(MaintenanceTicket.title)
    with lab.session() as s:
        rows=s.execute(query).all()
        check(rows==[('DIFFERENT','Reporter','Technician'),('SAME','Technician','Technician'),('UNASSIGNED','Reporter',None)],
              'Distinct aliases return different names, identical names, and NULL assignee correctly.')
        tickets=s.scalars(select(MaintenanceTicket).order_by(MaintenanceTicket.title)).all()
        check(tickets[1].reporter is tickets[1].assignee,'Both roles may resolve to the same identity-mapped User without mixing their meanings.')
        check(tickets[2].assignee is None,'Optional assignee navigation preserves the unassigned ticket.')
    with lab.engine.connect() as c:
        raw=c.execute(text(f'''SELECT t.title,r.display_name,a.display_name FROM {lab.schema}.maintenance_tickets t
            JOIN {lab.schema}.users r ON r.id=t.reported_by_id LEFT JOIN {lab.schema}.users a ON a.id=t.assigned_to_id ORDER BY t.title''')).all()
        check(raw==rows,'Raw SQL with two user aliases agrees with the ORM projection.')
    mapper=inspect(MaintenanceTicket)
    check({c.key for c in mapper.relationships.reporter.local_columns}=={'reported_by_id'}
          and {c.key for c in mapper.relationships.assignee.local_columns}=={'assigned_to_id'},'Each mapped relationship declares its own local foreign-key path.')
    check(not MaintenanceTicket.__table__.c.reported_by_id.nullable and MaintenanceTicket.__table__.c.assigned_to_id.nullable,
          'Required reporter and optional assignee retain their independent database nullability.')

if __name__=='__main__': run(23,scenario)
