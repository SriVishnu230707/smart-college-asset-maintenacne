"""Private local byte storage, scoped metadata, and compensated uploads."""
from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import re
from uuid import uuid4
from sqlalchemy import select
from college_maintenance.database import PROJECT_ROOT
from college_maintenance.models import TicketComment, TicketAttachment, WorkOrderAttachment, WorkOrder
from college_maintenance.reads import scope_for_actor
from college_maintenance.workflow import Conflict, NotFound, admin_scope, locked_ticket, nonblank
from college_maintenance.auditing import audit_change

class FileStore:
    def __init__(self, root=None):
        self.root = Path(root or PROJECT_ROOT/'.local/uploads'); self.root.mkdir(parents=True, exist_ok=True)
    def path(self, key):
        if not re.fullmatch('[0-9a-f]{32}', key): raise ValueError('Invalid storage key')
        return self.root/key
    def put(self, data):
        if not 0 < len(data) <= 1048576: raise ValueError('Attachment must contain 1-1048576 bytes')
        key = uuid4().hex
        with self.path(key).open('xb') as file: file.write(data)
        return key
    def remove(self, key): self.path(key).unlink(missing_ok=True)
    def read(self, metadata):
        try: data = self.path(metadata.storage_key).read_bytes()
        except FileNotFoundError: raise Conflict('Attachment content is unavailable') from None
        if len(data) != metadata.size or hashlib.sha256(data).hexdigest() != metadata.sha256:
            raise Conflict('Attachment content verification failed')
        return data

def comment_permission(actor, ticket):
    if ticket.status in {'closed','rejected'}: raise Conflict('Terminal tickets do not accept comments or photos')
    allowed = (actor.role == 'super_admin' or actor.role == 'department_admin' and actor.department_id == ticket.department_id
        or actor.role == 'technician' and ticket.assigned_to_id == actor.user_id
        or ticket.reported_by_id == actor.user_id and actor.department_id == ticket.department_id)
    if not allowed: raise PermissionError('Ticket mutation scope required')

def add_comment(session, actor_id, ticket_id, body, request_id=None):
    actor = scope_for_actor(session, actor_id); ticket = locked_ticket(session, actor, ticket_id)
    comment_permission(actor, ticket)
    comment = TicketComment(ticket_id=ticket.id, author_id=actor_id, body=nonblank(body,'comment',10000))
    session.add(comment); session.flush()
    audit_change(session, actor_id, 'comment_added', ticket=ticket, target_type='comment', target_id=comment.id, request_id=request_id)
    return dict(id=comment.id, ticket_id=ticket.id, author_id=actor_id, body=comment.body, created_at=comment.created_at)

def order_parent(session, actor, work_order_id, write=False):
    ticket_id = session.scalar(select(WorkOrder.ticket_id).where(WorkOrder.id == work_order_id))
    if ticket_id is None: raise NotFound('Work order not found')
    ticket = locked_ticket(session, actor, ticket_id)
    statement = select(WorkOrder).where(WorkOrder.id == work_order_id).execution_options(populate_existing=True)
    order = session.scalar(statement.with_for_update() if write else statement)
    if order is None: raise NotFound('Work order not found')
    if write:
        if actor.role != 'technician' or ticket.assigned_to_id != actor.user_id or order.technician_id != actor.user_id:
            raise PermissionError('Owning assigned technician required')
        if order.status == 'completed' or ticket.status not in {'assigned','in_progress'}:
            raise Conflict('Completed proof and work are immutable')
    elif actor.role == 'technician' and ticket.assigned_to_id == actor.user_id:
        pass
    else: admin_scope(actor, ticket.department_id)
    return ticket, order

def attachment_metadata(session, store, actor_id, owner_id, *, kind, storage_key, data, filename, content_type, request_id=None):
    actor = scope_for_actor(session, actor_id)
    filename = nonblank(filename, 'filename', 200)
    if any(ch in filename for ch in '/\\\r\n'): raise ValueError('Filename must be a plain name')
    content_type = nonblank(content_type,'content type',100)
    if kind == 'ticket':
        ticket = locked_ticket(session, actor, owner_id); comment_permission(actor, ticket)
        row = TicketAttachment(ticket_id=owner_id)
    elif kind == 'work_order':
        ticket, order = order_parent(session, actor, owner_id, write=True)
        row = WorkOrderAttachment(work_order_id=order.id)
    else: raise ValueError('Unknown attachment owner')
    row.storage_key=storage_key; row.filename=filename; row.content_type=content_type
    row.size=len(data); row.sha256=hashlib.sha256(data).hexdigest(); row.uploaded_by_id=actor_id
    store.read(row)  # Verify bytes before making any valid-looking metadata durable.
    session.add(row); session.flush()
    audit_change(session, actor_id, 'attachment_added', ticket=ticket, target_type=kind+'_attachment', target_id=row.id, request_id=request_id)
    return dict(id=row.id, filename=row.filename, size=row.size, content_type=row.content_type, sha256=row.sha256)

def read_attachment(session, store, actor_id, attachment_id, kind):
    actor=scope_for_actor(session, actor_id)
    model = TicketAttachment if kind == 'ticket' else WorkOrderAttachment
    row=session.get(model, attachment_id)
    if row is None: raise NotFound('Attachment not found')
    if kind == 'ticket': locked_ticket(session, actor, row.ticket_id)
    else: order_parent(session, actor, row.work_order_id)
    return store.read(row)

def cleanup_orphans(session, store, actor_id, minimum_age=timedelta(days=1), now=None):
    actor=scope_for_actor(session, actor_id)
    if actor.role != 'super_admin': raise PermissionError('Storage maintenance requires Super Admin')
    referenced=set(session.scalars(select(TicketAttachment.storage_key))) | set(session.scalars(select(WorkOrderAttachment.storage_key)))
    cutoff=(now or datetime.now(timezone.utc))-minimum_age; removed=[]
    for path in store.root.iterdir():
        if re.fullmatch('[0-9a-f]{32}',path.name) and path.name not in referenced and datetime.fromtimestamp(path.stat().st_mtime,timezone.utc)<cutoff:
            store.remove(path.name); removed.append(path.name)
    return removed
