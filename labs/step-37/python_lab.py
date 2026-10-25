"""Upload bytes first, authorize metadata, compensate failed DB work."""
import base64
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import event,select,func
from sqlalchemy.orm import Session
from college_maintenance.attachments import FileStore, cleanup_orphans
from college_maintenance.database import engine
from college_maintenance.migrations import upgrade
from college_maintenance.models import TicketAttachment, WorkOrder, MaintenanceTicket
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed,client,headers,report

def scenario(lab):
    ids=seed(lab)
    with TemporaryDirectory(dir=Path(__file__).resolve().parents[2]/'.local') as directory:
        store=FileStore(directory); data=b'synthetic attachment bytes'
        body=dict(filename='proof.bin',content_type='application/octet-stream',data_base64=base64.b64encode(data).decode())
        with client(lab,ids,storage=store) as api:
            key=report(api,ids).json()['id']
            comment=api.post(f'/tickets/{key}/comments',headers=headers('reporter'),json={'body':'Further details'})
            check(comment.status_code==201 and comment.json()['author_id']==str(ids['reporter']),'Comments derive their author from authenticated identity.')
            check(len(api.get(f'/tickets/{key}/comments',headers=headers('reporter')).json())==1,'An authorized ticket reader can page authored comments.')
            check(api.post(f'/tickets/{key}/comments',headers=headers('other'),json={'body':'Denied'}).status_code==404,'Comment access cannot bypass parent ticket scope.')
            uploaded=api.post(f'/ticket/{key}/attachments',headers=headers('reporter'),json=body)
            check(uploaded.status_code==201 and 'storage_key' not in uploaded.json(),'Ticket photo metadata commits only after content verification and conceals its private storage key.')
            attachment_id=uploaded.json()['id']
            check(api.get(f'/attachments/ticket/{attachment_id}',headers=headers('reporter')).content==data,'Authorized attachment download verifies bytes and content hash.')
            check(api.get(f'/attachments/ticket/{attachment_id}',headers=headers('other')).status_code==404,'A guessed attachment ID cannot bypass parent authorization.')
            before={p.name for p in store.root.iterdir()}
            def fail(session,ctx,instances):
                if any(isinstance(row,TicketAttachment) for row in session.new): raise RuntimeError('synthetic metadata failure')
            event.listen(Session,'before_flush',fail)
            try:
                try: api.post(f'/ticket/{key}/attachments',headers=headers('reporter'),json=body)
                except RuntimeError: check(True,'A metadata persistence failure escapes the operation owner.')
                else: raise AssertionError('Metadata failure swallowed')
            finally:event.remove(Session,'before_flush',fail)
            check(before=={p.name for p in store.root.iterdir()},'Failed database work compensates only its newly staged object.')
            with lab.session() as s,s.begin():
                ticket=s.get(MaintenanceTicket,UUID(key));ticket.status='assigned';ticket.assigned_to_id=ids['tech']
                order=WorkOrder(ticket_id=ticket.id,technician_id=ids['tech']);s.add(order);s.flush();order_id=order.id
            proof=api.post(f'/work_order/{order_id}/attachments',headers=headers('tech'),json=body)
            check(proof.status_code==201,'The owning assigned technician can add separate work-order proof.')
            check(api.get(f"/attachments/work_order/{proof.json()['id']}",headers=headers('reporter')).status_code==403,'Ticket reporter access does not grant work-order proof access.')
            with lab.session() as s,s.begin(): s.get(MaintenanceTicket,UUID(key)).status='closed'
            check(api.post(f'/tickets/{key}/comments',headers=headers('reporter'),json={'body':'Too late'}).status_code==409,'Terminal tickets preserve their append-only comment history.')
        orphan=store.put(b'orphan after process crash')
        with lab.session() as s,s.begin():
            removed=cleanup_orphans(s,store,ids['super'],now=datetime.now(timezone.utc)+timedelta(days=2))
            check(removed==[orphan] and len(list(store.root.iterdir()))==2,'Age-gated orphan cleanup removes unreferenced uploads and preserves referenced content.')
        with lab.session() as s:
            row=s.scalars(select(TicketAttachment)).one();store.remove(row.storage_key)
            try:store.read(row)
            except Exception as error:check('unavailable' in str(error),'Missing stored content is detected rather than returned as a valid attachment.')
            else:raise AssertionError('Missing object accepted')
    with engine.begin() as c:upgrade(c)

if __name__=='__main__':run(37,scenario)
