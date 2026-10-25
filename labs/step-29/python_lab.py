"""Compare explicit DTO reads with SQL and contract-derived access predicates."""
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import text
from college_maintenance.models import Asset, MaintenanceTicket, User
from college_maintenance.reads import asset_detail, department_tickets, scope_for_actor, technician_assignments, ticket_query
from labs.shared.orm_lab import check,run

def scenario(lab):
    ids=lab.seed()
    with lab.session() as s,s.begin():
        admin=User(email='admin@example.test',display_name='Department Admin',role='department_admin',department_id=ids['dept'],password_hash='synthetic_phase_hash')
        superuser=User(email='super@example.test',display_name='Super Admin',role='super_admin',password_hash='synthetic_phase_hash')
        other_asset=Asset(asset_code='ECE-PC',name='Other computer',department_id=ids['other_dept'],category_id=ids['category'])
        s.add_all([admin,superuser,other_asset]);s.flush();admin_id,super_id,other_asset_id=admin.id,superuser.id,other_asset.id
        s.add_all([
            MaintenanceTicket(asset_id=ids['asset'],reported_by_id=ids['reporter'],assigned_to_id=ids['tech'],department_id=ids['dept'],title='ASSIGNED',description='Read fixture',priority='high',status='assigned',assigned_at=datetime.now(timezone.utc)),
            MaintenanceTicket(asset_id=ids['asset'],reported_by_id=ids['tech'],department_id=ids['dept'],title='OWN-TECH',description='Read fixture',priority='low'),
            MaintenanceTicket(asset_id=other_asset_id,reported_by_id=ids['other'],department_id=ids['other_dept'],title='OTHER-DEPT',description='Read fixture',priority='medium')])
    with lab.session() as s:
        student=scope_for_actor(s,ids['reporter']);tech=scope_for_actor(s,ids['tech']);admin=scope_for_actor(s,admin_id);superuser=scope_for_actor(s,super_id)
        check(asset_detail(s,student,ids['asset']).category_code=='COMPUTER','Asset detail projects required department/category data explicitly.')
        check(asset_detail(s,student,other_asset_id) is None and asset_detail(s,student,uuid4()) is None,'Missing and unauthorized asset details both return None without widening scope.')
        check(asset_detail(s,superuser,other_asset_id).department_code=='ECE','Super Admin can read the other department asset.')
        check({t.title for t in department_tickets(s,student,ids['dept'])}=={'ASSIGNED'},'Student ticket reads expose only the actor\'s own reports.')
        check({t.title for t in department_tickets(s,tech,ids['dept'])}=={'ASSIGNED','OWN-TECH'},'Technician ticket scope combines assigned and own reports.')
        check(len(department_tickets(s,admin,ids['dept']))==2 and not department_tickets(s,admin,ids['other_dept']),
              'Department filtering intersects administrator scope and cannot expand it.')
        rows=department_tickets(s,superuser,ids['dept'],status='open')
        check(len(rows)==1 and rows[0].assignee_name is None and rows[0].title=='OWN-TECH','Nullable assignee projection retains unassigned tickets under status filters.')
        check([t.title for t in technician_assignments(s,tech)]==['ASSIGNED'],'Technician assignment reads return only assigned work, not merely own reports.')
        try:technician_assignments(s,tech,ids['other'])
        except PermissionError:check(True,'A technician cannot request another actor\'s assignment list.')
        else:raise AssertionError('Assignment scope bypass')
        try:department_tickets(s,superuser,ids['dept'],status="open' OR 1=1")
        except ValueError:check(True,'Unknown filter values are rejected before statement execution.')
        else:raise AssertionError('Invalid filter accepted')
        projected=department_tickets(s,superuser,ids['dept'])
        check(all('password' not in key and 'email' not in key for key in vars(projected[0])),'Response projections contain no password hashes or unrestricted user records.')
        with s.no_autoflush:
            raw=s.execute(text(f'''SELECT t.title,r.display_name,a.display_name FROM {lab.schema}.maintenance_tickets t
                JOIN {lab.schema}.users r ON r.id=t.reported_by_id LEFT JOIN {lab.schema}.users a ON a.id=t.assigned_to_id
                WHERE t.department_id=:dept ORDER BY t.title'''),{'dept':ids['dept']}).all()
        check(sorted((r.title,r.reporter_name,r.assignee_name) for r in projected)==raw,'Raw SQL and ORM projections agree for required and nullable paths.')
    check(projected[0].title and projected[0].created_at.utcoffset() is not None,'DTO values remain available after Session closure without lazy loading.')
    with lab.session() as s,s.begin():s.get(User,ids['reporter']).department_id=ids['other_dept']
    with lab.session() as s:
        moved=scope_for_actor(s,ids['reporter'])
        check([t.title for t in department_tickets(s,moved,ids['dept'])]==['ASSIGNED'],'A reporter retains own ticket history after a department change.')
    with lab.session() as s,s.begin():s.get(User,ids['other']).is_active=False
    with lab.session() as s:
        try:scope_for_actor(s,ids['other'])
        except PermissionError:check(True,'Inactive actors cannot obtain a read scope.')
        else:raise AssertionError('Inactive actor accepted')

if __name__=='__main__':run(29,scenario)
