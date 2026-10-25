"""Direct HTTP requests exercise role and target-resource policy."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import select, func
from college_maintenance.models import MaintenanceTicket, User, Asset
from labs.shared.orm_lab import check, run
from labs.shared.workflow_lab import seed, client, headers, report

def scenario(lab):
    ids=seed(lab)
    with client(lab,ids) as api:
        response=report(api,ids); check(response.status_code==201,'A student can report an eligible department asset.')
        ticket=response.json(); key=ticket['id']
        check(ticket['reported_by_id']==str(ids['reporter']) and ticket['department_id']==str(ids['dept']),'Server identity and asset ownership determine permanent ticket attribution.')
        check(report(api,ids,reported_by_id=str(ids['other']),department_id=str(ids['other_dept'])).status_code==422,'Caller overrides for reporter or department are rejected by the transport schema.')
        for actor in ('other','other_admin','tech'):
            check(api.get(f'/tickets/{key}',headers=headers(actor)).status_code==404,f'{actor} cannot read a ticket outside their own/assigned/department scope.')
        check(api.patch(f'/tickets/{key}/priority',headers=headers('reporter'),json={'priority':'critical','expected_version':1}).status_code==403,'Reporter status does not grant administrator triage permission.')
        check(api.patch(f'/tickets/{key}/priority',headers=headers('other_admin'),json={'priority':'critical','expected_version':1}).status_code==404,'Cross-department administrators cannot mutate the target ticket.')
        check(api.patch(f'/tickets/{key}/priority',headers=headers('admin'),json={'priority':'critical','expected_version':1}).status_code==200,'An in-scope administrator may triage priority.')
        check(api.get(f'/tickets/{key}',headers=headers('super')).status_code==200,'Super Admin can read across department scope.')
        check(report(api,ids,actor='other').status_code==404,'Cross-department reporting is denied independently of UI controls.')
        check(api.patch(f'/tickets/{key}/report',headers=headers('admin'),json={'title':'Changed','description':'No','expected_version':1}).status_code==403,'Administrative scope does not grant ownership of original report text.')
        with lab.session() as session, session.begin(): session.get(User,ids['reporter']).department_id=ids['other_dept']
        check(api.get(f'/tickets/{key}',headers=headers('reporter')).status_code==200,'A transferred reporter retains read access to their own history.')
        check(api.patch(f'/tickets/{key}/report',headers=headers('reporter'),json={'title':'Changed','description':'No','expected_version':1}).status_code==403,'Transferred reporter history access does not grant mutation permission.')
        with lab.session() as session,session.begin(): session.get(Asset,ids['asset']).status='retired'
        check(report(api,ids,actor='super').status_code==409,'Even Super Admin cannot report a retired asset.')
    with lab.session() as session:
        check(session.scalar(select(func.count()).select_from(MaintenanceTicket))==1,'Denied requests leave no extra ticket rows.')

if __name__=='__main__': run(34,scenario)
