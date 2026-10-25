"""Exercise administrative state edges; repair edges are work-order commands."""
import sys
from pathlib import Path
from uuid import UUID
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from college_maintenance.database import engine
from college_maintenance.migrations import upgrade
from college_maintenance.models import MaintenanceTicket, WorkOrder, User
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed,client,headers,report

def scenario(lab):
    ids=seed(lab)
    with client(lab,ids) as api:
        key=report(api,ids).json()['id']
        def act(action,actor='admin',**values): return api.post(f'/tickets/{key}/transitions',headers=headers(actor),json=dict(action=action,**values))
        check(act('assign',technician_id=str(ids['reporter'])).status_code==400,'An existing student ID is not an eligible assignee.')
        check(act('assign',technician_id=str(ids['other_tech'])).status_code==400,'A technician from another department is ineligible.')
        with lab.session() as s,s.begin(): s.get(User,ids['tech']).is_active=False
        check(act('assign',technician_id=str(ids['tech'])).status_code==400,'Inactive technicians cannot receive assignments.')
        with lab.session() as s,s.begin(): s.get(User,ids['tech']).is_active=True
        check(act('assign',actor='reporter',technician_id=str(ids['tech'])).status_code==403,'A reporter cannot approve their own report.')
        check(act('assign',technician_id=str(ids['tech'])).json()['status']=='assigned','Approval and eligible assignment form one transition.')
        check(act('reject',reason='Too late').status_code==409,'Assigned tickets cannot take the open-only rejection path.')
        check(act('verify',reason='Premature').status_code==409,'Verification cannot skip the repair workflow.')
        with lab.session() as s,s.begin():
            order=WorkOrder(ticket_id=UUID(key),technician_id=ids['tech']);s.add(order);s.flush();order_id=order.id
        check(act('assign',technician_id=str(ids['tech'])).status_code==409,'An existing draft prevents reassignment.')
        with lab.session() as s,s.begin():
            s.get(WorkOrder,order_id).status='completed';s.get(MaintenanceTicket,UUID(key)).status='awaiting_verification'
        check(act('rework',reason=' ').status_code==400,'Rework requires a nonblank recorded reason.')
        check(act('rework',reason='Issue remains').json()['status']=='in_progress','Rework returns the ticket to repair while preserving completed history.')
        with lab.session() as s,s.begin(): s.get(MaintenanceTicket,UUID(key)).status='awaiting_verification'
        check(act('verify',reason='Verified repair').json()['status']=='closed','An administrator can close a repair with completed work and a note.')
        check(act('assign',technician_id=str(ids['tech'])).status_code==409,'Terminal tickets cannot be reopened through assignment.')
        rejected=report(api,ids).json()['id']
        response=api.post(f'/tickets/{rejected}/transitions',headers=headers('admin'),json={'action':'reject','reason':'Duplicate issue'})
        check(response.json()['status']=='rejected','The open report rejection path records a terminal outcome.')
    with lab.session() as s:
        ticket=s.get(MaintenanceTicket,UUID(key))
        check(ticket.closed_at is not None and ticket.verification_note=='Verified repair' and ticket.rework_reason=='Issue remains','Verification and rework notes survive as distinct historical fields.')
    with engine.begin() as c: upgrade(c)

if __name__=='__main__':run(35,scenario)
