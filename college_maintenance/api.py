"""Thin synchronous FastAPI boundary. One transaction owner per operation."""
from dataclasses import asdict
from uuid import UUID, uuid4
from fastapi import Depends, FastAPI, HTTPException, Query, Header
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.exc import IntegrityError, DBAPIError
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
import base64
from datetime import date
from college_maintenance.analytics import ranked_failures_query,monthly_costs_query
from fastapi.responses import Response
from college_maintenance.attachments import FileStore, add_comment, attachment_metadata, read_attachment
from college_maintenance.loading import comment_page
from college_maintenance.inventory import add_supplier, create_part, move_stock, part_result, inventory_admin, reconciliation_query
from college_maintenance.models import SparePart
from college_maintenance.repairs import create_order, start_order, edit_order, set_part_line, remove_part_line, discard_order, order_result
from college_maintenance.attachments import order_parent
from college_maintenance.completion import complete_work_order
from college_maintenance.retries import RETRYABLE
from sqlalchemy.orm.exc import StaleDataError
from college_maintenance.reports import cost_rows,failure_frequency_query
from college_maintenance.advanced_reports import latest_comments_query
from college_maintenance.authentication import authenticate_token
from college_maintenance.pagination import ticket_feed
from college_maintenance.models import MaintenanceTicket, AuditEvent
from sqlalchemy import select
from college_maintenance.reads import asset_detail, scope_for_actor, ticket_query
from college_maintenance.sessions import SessionFactory
from college_maintenance.workflow import Conflict, NotFound, report_ticket, edit_report, triage_ticket, ticket_result, transition_ticket, locked_ticket, admin_scope

class ReportInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    asset_id: UUID
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    priority: Literal['low','medium','high','critical'] = 'medium'

class EditInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=10000)
    expected_version: int = Field(ge=1,strict=True)

class PriorityInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    priority: Literal['low','medium','high','critical']
    expected_version: int = Field(ge=1,strict=True)

class TransitionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['assign','reject','verify','rework']
    technician_id: UUID | None = None
    reason: str | None = Field(None, max_length=10000)

class CommentInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    body: str = Field(min_length=1, max_length=10000)

class AttachmentInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    filename: str = Field(min_length=1,max_length=200)
    content_type: str = Field(min_length=1,max_length=100)
    data_base64: str = Field(min_length=1,max_length=1398104)

class SupplierInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    name: str = Field(min_length=1,max_length=150)
    contact: str = Field(min_length=1,max_length=1000)

class PartInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    sku: str = Field(min_length=1,max_length=50)
    name: str = Field(min_length=1,max_length=150)
    unit_cost: str
    opening: int = Field(0,ge=0,le=2147483647,strict=True)
    reorder_level: int = Field(0,ge=0,le=2147483647,strict=True)

class MovementInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    kind: Literal['receipt','adjustment']
    delta: int = Field(strict=True,ge=-2147483647,le=2147483647)
    supplier_id: UUID | None = None
    reason: str | None = Field(None,max_length=10000)

class OrderInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    labor_cost: str
    completion_note: str | None = Field(None,max_length=10000)

class LineInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    quantity: int = Field(strict=True,ge=1,le=2147483647)

class CompletionInput(BaseModel):
    model_config=ConfigDict(extra='forbid')

def create_app(session_factory=SessionFactory, authenticate=authenticate_token, storage=None):
    app = FastAPI(title='College maintenance API', version='0.1.0')
    store = storage or FileStore()
    bearer = HTTPBearer(auto_error=False)

    def actor_id(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        identity = authenticate(credentials.credentials) if credentials else None
        if identity is None:
            raise HTTPException(401, 'Valid bearer authentication required', headers={'WWW-Authenticate':'Bearer'})
        return identity

    def session_dependency():
        with session_factory() as session:
            yield session

    from college_maintenance.dashboard import install_dashboard
    install_dashboard(app, actor_id, session_dependency)

    @app.get('/health/ready')
    def ready(session=Depends(session_dependency)):
        with session.begin():session.execute(select(1)).scalar_one()
        return {'database':'ready'}

    def request_identifier(x_request_id: UUID | None = Header(None)):
        return x_request_id or uuid4()

    @app.exception_handler(PermissionError)
    def forbidden(request, error): return JSONResponse(status_code=403, content={'detail':'Permission denied'})

    @app.exception_handler(ValueError)
    def invalid(request, error): return JSONResponse(status_code=400, content={'detail':str(error)})

    @app.exception_handler(IntegrityError)
    def conflict(request, error): return JSONResponse(status_code=409, content={'detail':'Database integrity conflict'})

    @app.exception_handler(DBAPIError)
    def database_error(request,error):
        if getattr(error.orig,'sqlstate',None) in RETRYABLE:
            return JSONResponse(status_code=503,content={'detail':'Transaction retry limit reached'},headers={'Retry-After':'1'})
        return JSONResponse(status_code=500,content={'detail':'Database operation failed'})

    @app.exception_handler(Conflict)
    def state_conflict(request, error): return JSONResponse(status_code=409, content={'detail':str(error)})

    @app.exception_handler(StaleDataError)
    def stale_edit(request,error):return JSONResponse(status_code=409,content={'detail':'Stale ticket version; reload before editing'})

    @app.exception_handler(NotFound)
    def not_found(request, error): return JSONResponse(status_code=404, content={'detail':'Resource not found'})

    @app.post('/tickets', status_code=201)
    def post_ticket(body: ReportInput, identity=Depends(actor_id), session=Depends(session_dependency), request_id=Depends(request_identifier)):
        with session.begin():
            return ticket_result(report_ticket(session, identity, request_id=request_id, **body.model_dump()))

    @app.patch('/tickets/{ticket_id}/report')
    def patch_report(ticket_id: UUID, body: EditInput, identity=Depends(actor_id), session=Depends(session_dependency), request_id=Depends(request_identifier)):
        with session.begin():
            return ticket_result(edit_report(session, identity, ticket_id, request_id=request_id, **body.model_dump()))

    @app.patch('/tickets/{ticket_id}/priority')
    def patch_priority(ticket_id: UUID, body: PriorityInput, identity=Depends(actor_id), session=Depends(session_dependency), request_id=Depends(request_identifier)):
        with session.begin():
            return ticket_result(triage_ticket(session, identity, ticket_id, body.priority, expected_version=body.expected_version, request_id=request_id))

    @app.post('/tickets/{ticket_id}/transitions')
    def post_transition(ticket_id: UUID, body: TransitionInput, identity=Depends(actor_id), session=Depends(session_dependency), request_id=Depends(request_identifier)):
        with session.begin():
            return ticket_result(transition_ticket(session, identity, ticket_id, request_id=request_id, **body.model_dump()))

    @app.get('/tickets/{ticket_id}/audit')
    def get_audit(ticket_id: UUID, limit: int = Query(20, ge=1, le=100), identity=Depends(actor_id), session=Depends(session_dependency)):
        with session.begin():
            actor = scope_for_actor(session, identity); ticket = locked_ticket(session, actor, ticket_id)
            admin_scope(actor, ticket.department_id)
            query = select(AuditEvent.id, AuditEvent.actor_id, AuditEvent.action, AuditEvent.department_id, AuditEvent.request_id,
                AuditEvent.target_type, AuditEvent.target_id, AuditEvent.occurred_at, AuditEvent.payload).where(AuditEvent.ticket_id == ticket.id)
            return [dict(row) for row in session.execute(query.order_by(AuditEvent.occurred_at, AuditEvent.id).limit(limit)).mappings()]

    @app.get('/assets/{asset_id}')
    def get_asset(asset_id: UUID, identity=Depends(actor_id), session=Depends(session_dependency)):
        with session.begin():
            result = asset_detail(session, scope_for_actor(session, identity), asset_id)
            if result is None: raise HTTPException(404, 'Asset not found')
            return asdict(result)

    @app.post('/suppliers',status_code=201)
    def post_supplier(body: SupplierInput, identity=Depends(actor_id),session=Depends(session_dependency),request_id=Depends(request_identifier)):
        with session.begin():return add_supplier(session,identity,request_id=request_id,**body.model_dump())

    @app.post('/tickets/{ticket_id}/work-orders',status_code=201)
    def post_order(ticket_id: UUID,identity=Depends(actor_id),session=Depends(session_dependency),request_id=Depends(request_identifier)):
        with session.begin():return order_result(session,create_order(session,identity,ticket_id,request_id=request_id))

    @app.get('/work-orders/{order_id}')
    def get_order(order_id: UUID,identity=Depends(actor_id),session=Depends(session_dependency)):
        with session.begin():
            ticket,order=order_parent(session,scope_for_actor(session,identity),order_id)
            return order_result(session,order)

    @app.post('/work-orders/{order_id}/start')
    def post_start(order_id: UUID,identity=Depends(actor_id),session=Depends(session_dependency),request_id=Depends(request_identifier)):
        with session.begin():return order_result(session,start_order(session,identity,order_id,request_id=request_id))

    @app.post('/work-orders/{order_id}/complete')
    def post_complete(order_id: UUID,body: CompletionInput=CompletionInput(),identity=Depends(actor_id),request_id=Depends(request_identifier)):
        return complete_work_order(store,identity,order_id,session_factory=session_factory,request_id=request_id)

    @app.patch('/work-orders/{order_id}')
    def patch_order(order_id: UUID,body: OrderInput,identity=Depends(actor_id),session=Depends(session_dependency),request_id=Depends(request_identifier)):
        with session.begin():return order_result(session,edit_order(session,identity,order_id,request_id=request_id,**body.model_dump()))

    @app.put('/work-orders/{order_id}/parts/{part_id}')
    def put_line(order_id: UUID,part_id: UUID,body: LineInput,identity=Depends(actor_id),session=Depends(session_dependency),request_id=Depends(request_identifier)):
        with session.begin():return order_result(session,set_part_line(session,identity,order_id,part_id,body.quantity,request_id=request_id))

    @app.delete('/work-orders/{order_id}/parts/{part_id}')
    def delete_line(order_id: UUID,part_id: UUID,identity=Depends(actor_id),session=Depends(session_dependency),request_id=Depends(request_identifier)):
        with session.begin():return order_result(session,remove_part_line(session,identity,order_id,part_id,request_id=request_id))

    @app.delete('/work-orders/{order_id}')
    def delete_order(order_id: UUID,identity=Depends(actor_id),session=Depends(session_dependency),request_id=Depends(request_identifier)):
        with session.begin():return discard_order(session,identity,order_id,request_id=request_id)

    @app.post('/parts',status_code=201)
    def post_part(body: PartInput,identity=Depends(actor_id),session=Depends(session_dependency),request_id=Depends(request_identifier)):
        with session.begin():return part_result(create_part(session,identity,request_id=request_id,**body.model_dump()))

    @app.get('/parts')
    def get_parts(limit: int=Query(20,ge=1,le=100),identity=Depends(actor_id),session=Depends(session_dependency)):
        with session.begin():
            if scope_for_actor(session,identity).role=='student':raise PermissionError('Parts catalog requires staff access')
            return [part_result(part) for part in session.scalars(select(SparePart).order_by(SparePart.id).limit(limit))]

    @app.post('/parts/{part_id}/movements')
    def post_movement(part_id: UUID,body: MovementInput,identity=Depends(actor_id),session=Depends(session_dependency),request_id=Depends(request_identifier)):
        with session.begin():return part_result(move_stock(session,identity,part_id,request_id=request_id,**body.model_dump()))

    @app.get('/inventory/reconciliation')
    def get_reconciliation(identity=Depends(actor_id),session=Depends(session_dependency)):
        with session.begin():
            inventory_admin(session,identity)
            return [dict(row) for row in session.execute(reconciliation_query()).mappings()]

    @app.get('/reports/costs')
    def get_costs(limit: int=Query(100,ge=1,le=100),identity=Depends(actor_id),session=Depends(session_dependency)):
        with session.begin():return cost_rows(session,scope_for_actor(session,identity),limit)

    @app.get('/reports/failures')
    def get_failures(limit: int=Query(100,ge=1,le=100),identity=Depends(actor_id),session=Depends(session_dependency)):
        with session.begin():
            return [dict(row) for row in session.execute(failure_frequency_query(scope_for_actor(session,identity)).limit(limit)).mappings()]

    @app.get('/reports/latest-comments')
    def get_latest_comments(strategy: Literal['lateral','distinct_on','scalar']='lateral',limit: int=Query(20,ge=1,le=100),identity=Depends(actor_id),session=Depends(session_dependency)):
        with session.begin():
            return [dict(row) for row in session.execute(latest_comments_query(scope_for_actor(session,identity),strategy).limit(limit)).mappings()]

    @app.get('/reports/ranked-failures')
    def ranked_failures(top: int=Query(3,ge=1,le=100),include_ties: bool=True,limit:int=Query(100,ge=1,le=100),identity=Depends(actor_id),session=Depends(session_dependency)):
        with session.begin():
            return [dict(row) for row in session.execute(ranked_failures_query(scope_for_actor(session,identity),top=top,include_ties=include_ties).limit(limit)).mappings()]

    @app.get('/reports/monthly-costs')
    def monthly_costs(start:date,end:date,zone:Literal['UTC','Asia/Kolkata']='Asia/Kolkata',identity=Depends(actor_id),session=Depends(session_dependency)):
        with session.begin():
            rows=session.execute(monthly_costs_query(scope_for_actor(session,identity),start,end,zone)).mappings()
            return [{**row,'cost':format(row['cost'],'.2f'),'change':None if row['change'] is None else format(row['change'],'.2f')} for row in rows]

    @app.post('/tickets/{ticket_id}/comments', status_code=201)
    def post_comment(ticket_id: UUID, body: CommentInput, identity=Depends(actor_id), session=Depends(session_dependency), request_id=Depends(request_identifier)):
        with session.begin(): return add_comment(session, identity, ticket_id, body.body, request_id=request_id)

    @app.get('/tickets/{ticket_id}/comments')
    def get_comments(ticket_id: UUID, limit: int = Query(20,ge=1,le=100), offset: int = Query(0,ge=0,le=100000), identity=Depends(actor_id), session=Depends(session_dependency)):
        with session.begin():
            actor=scope_for_actor(session,identity); locked_ticket(session,actor,ticket_id)
            return [dict(row) for row in comment_page(session,actor,ticket_id,limit=limit,offset=offset)]

    @app.post('/{kind}/{owner_id}/attachments', status_code=201)
    def post_attachment(kind: Literal['ticket','work_order'], owner_id: UUID, body: AttachmentInput, identity=Depends(actor_id), session=Depends(session_dependency), request_id=Depends(request_identifier)):
        data=base64.b64decode(body.data_base64,validate=True); key=store.put(data)
        try:
            with session.begin():
                result=attachment_metadata(session,store,identity,owner_id,kind=kind,storage_key=key,data=data,filename=body.filename,content_type=body.content_type,request_id=request_id)
        except BaseException:
            store.remove(key); raise
        return result

    @app.get('/attachments/{kind}/{attachment_id}')
    def get_attachment(kind: Literal['ticket','work_order'], attachment_id: UUID, identity=Depends(actor_id), session=Depends(session_dependency)):
        with session.begin(): data=read_attachment(session,store,identity,attachment_id,kind)
        return Response(content=data,media_type='application/octet-stream',headers={'Content-Disposition':'attachment'})

    @app.get('/tickets')
    def list_tickets(limit: int = Query(20, ge=1, le=100), cursor: str | None = None, department_id: UUID | None = None,
                     status: str | None = None, priority: str | None = None,
                     identity=Depends(actor_id), session=Depends(session_dependency)):
        with session.begin():
            return asdict(ticket_feed(session, scope_for_actor(session, identity), limit=limit, cursor=cursor,
                department_id=department_id, status=status, priority=priority))

    @app.get('/tickets/search')
    def search_tickets(q:str=Query(min_length=1,max_length=200),limit:int=Query(20,ge=1,le=100),identity=Depends(actor_id),session=Depends(session_dependency)):
        from college_maintenance.search import search_tickets_query
        with session.begin():
            return [dict(row) for row in session.execute(search_tickets_query(scope_for_actor(session,identity),q,limit)).mappings()]

    @app.get('/tickets/{ticket_id}')
    def get_ticket(ticket_id: UUID, identity=Depends(actor_id), session=Depends(session_dependency)):
        with session.begin():
            query = ticket_query(scope_for_actor(session, identity)).add_columns(MaintenanceTicket.version, MaintenanceTicket.description).where(MaintenanceTicket.id == ticket_id)
            result = session.execute(query).mappings().one_or_none()
            if result is None: raise HTTPException(404, 'Ticket not found')
            return dict(result)

    return app

app = create_app()
