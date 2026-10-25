"""A success event cannot outlive a rolled-back business mutation."""
import sys
from pathlib import Path
from uuid import UUID, uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import event, select, func
from sqlalchemy.orm import Session
from college_maintenance.database import engine
from college_maintenance.migrations import upgrade
from college_maintenance.models import AuditEvent, MaintenanceTicket
from labs.shared.orm_lab import check, run
from labs.shared.workflow_lab import seed,client,headers,report

def scenario(lab):
    ids=seed(lab); request_id=uuid4()
    with client(lab,ids) as api:
        key=report(api,ids).json()['id']
        response=api.patch(f'/tickets/{key}/priority',headers={**headers('admin'),'X-Request-ID':str(request_id)},json={'priority':'critical'})
        check(response.status_code==200,'A successful priority change commits through the API.')
        history=api.get(f'/tickets/{key}/audit',headers=headers('admin')).json()
        check(len(history)==2,'Report creation and priority mutation each create one business success event.')
        entry=next(e for e in history if e['action']=='ticket_priority_changed')
        check(entry['request_id']==str(request_id) and entry['actor_id']==str(ids['admin']),'Audit retains authenticated actor and validated request correlation.')
        check(entry['department_id']==str(ids['dept']) and entry['target_type']=='ticket' and entry['target_id']==key,'Audit target and permanent ticket department are explicit.')
        check(entry['payload']=={'before':'medium','after':'critical'},'Audit details record the successful before/after values.')
        check(api.get(f'/tickets/{key}/audit',headers=headers('reporter')).status_code==403,'Reporter ticket visibility does not grant business audit access.')
        check(api.get(f'/tickets/{key}/audit',headers=headers('other_admin')).status_code==404,'Department audit access cannot reveal another department event.')
        def fail_before_audit(session, flush_context, instances):
            if any(isinstance(row,AuditEvent) and row.action=='ticket_priority_changed' for row in session.new):
                raise RuntimeError('synthetic audit failure')
        event.listen(Session,'before_flush',fail_before_audit)
        try:
            try: api.patch(f'/tickets/{key}/priority',headers=headers('admin'),json={'priority':'low'})
            except RuntimeError as error: check('synthetic audit failure' in str(error),'An audit persistence failure propagates through the transaction owner.')
            else: raise AssertionError('Audit failure swallowed')
        finally: event.remove(Session,'before_flush',fail_before_audit)
    driver=lab.driver()
    row=driver.execute(f'SELECT priority,(SELECT count(*) FROM {lab.schema}.audit_events) FROM {lab.schema}.maintenance_tickets WHERE id=%s',(UUID(key),)).fetchone()
    check(row==('critical',2),'A fresh independent connection sees neither the failed priority change nor a success event.')
    with engine.begin() as connection: upgrade(connection)

if __name__=='__main__':run(36,scenario)
