"""Independent optional booking feature: explicit migration, services and API."""
from contextlib import contextmanager
from pathlib import Path
from datetime import datetime
from uuid import UUID
import re
from fastapi import FastAPI,Depends,HTTPException,Query
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer,HTTPAuthorizationCredentials
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import Integer,Identity,ForeignKey,Computed,select,text
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column
from sqlalchemy.dialects.postgresql import TSTZRANGE,INT4RANGE,Range
from sqlalchemy.exc import IntegrityError
from college_maintenance.models import Asset,Department,User,AuditEvent
from college_maintenance.reads import scope_for_actor
from college_maintenance.workflow import Conflict

class Mapping(DeclarativeBase):pass
class BookingKey(Mapping):
    __tablename__='booking_keys'
    id:Mapped[int]=mapped_column(Integer,Identity(always=True),primary_key=True)
    asset_id:Mapped[UUID]=mapped_column(ForeignKey(Asset.id),unique=True)
class Booking(Mapping):
    __tablename__='preventive_bookings'
    id:Mapped[UUID]=mapped_column(primary_key=True,server_default=text('gen_random_uuid()'))
    asset_key:Mapped[int]=mapped_column(ForeignKey('booking_keys.id'))
    department_id:Mapped[UUID]=mapped_column(ForeignKey(Department.id))
    requested_by_id:Mapped[UUID]=mapped_column(ForeignKey(User.id))
    request_key:Mapped[UUID]=mapped_column(unique=True)
    slot:Mapped[Range]=mapped_column(TSTZRANGE)
    asset_span:Mapped[Range]=mapped_column(INT4RANGE,Computed("int4range(asset_key,asset_key,'[]')",persisted=True))
    reason:Mapped[str]
    status:Mapped[str]=mapped_column(server_default=text("'scheduled'"))
    version:Mapped[int]=mapped_column(server_default=text('1'))

@contextmanager
def feature_schema(lab):
    if not re.fullmatch(r'college_step80',lab.schema):raise ValueError('Exact feature study schema required')
    source=Path(__file__).with_name('migration.sql').read_text(encoding='utf-8').replace('{schema}',lab.schema)
    with lab.engine.begin() as c:
        for statement in source.split(';'):
            if statement.strip():c.exec_driver_sql(statement)
    try:yield
    finally:
        with lab.engine.begin() as c:
            for name in ('preventive_bookings','booking_keys','booking_revision'):c.exec_driver_sql(f'DROP TABLE {lab.schema}.{name}')

def administrator(session,actor_id):
    actor=scope_for_actor(session,actor_id)
    if actor.role not in {'department_admin','super_admin'}:raise PermissionError('Scheduling requires administration')
    return actor

def dto(booking,asset_id):
    return dict(id=str(booking.id),asset_id=str(asset_id),department_id=str(booking.department_id),
        start=booking.slot.lower.isoformat(),end=booking.slot.upper.isoformat(),reason=booking.reason,status=booking.status,version=booking.version)

def schedule(session,actor_id,asset_id,start,end,reason,request_key):
    actor=administrator(session,actor_id)
    if start.utcoffset() is None or end.utcoffset() is None or not start<end:raise ValueError('Use increasing aware instants')
    reason=reason.strip()
    if not 1<=len(reason)<=500:raise ValueError('Reason required')
    asset=session.scalar(select(Asset).where(Asset.id==asset_id).with_for_update().execution_options(populate_existing=True))
    if asset is None or actor.role!='super_admin' and actor.department_id!=asset.department_id:raise LookupError('Asset unavailable')
    key=session.scalar(select(BookingKey).where(BookingKey.asset_id==asset_id))
    if key is None:
        key=BookingKey(asset_id=asset_id);session.add(key);session.flush()
    interval=Range(start,end,bounds='[)')
    existing=session.scalar(select(Booking).where(Booking.request_key==request_key))
    if existing:
        if (existing.requested_by_id,existing.asset_key,existing.slot,existing.reason)!=(actor_id,key.id,interval,reason):raise Conflict('Request key payload differs')
        return dto(existing,asset_id),False
    booking=Booking(asset_key=key.id,department_id=asset.department_id,requested_by_id=actor_id,request_key=request_key,slot=interval,reason=reason)
    session.add(booking);session.flush()
    session.add(AuditEvent(actor_id=actor_id,asset_id=asset_id,department_id=asset.department_id,target_type='preventive_booking',target_id=booking.id,
        action='preventive_slot_booked',request_id=request_key,payload={'start':start.isoformat(),'end':end.isoformat()}));session.flush()
    return dto(booking,asset_id),True

def cancel(session,actor_id,identity,expected_version):
    actor=administrator(session,actor_id)
    booking=session.get(Booking,identity,with_for_update=True,populate_existing=True)
    if booking is None or actor.role!='super_admin' and actor.department_id!=booking.department_id:raise LookupError('Booking unavailable')
    asset=session.scalar(select(BookingKey.asset_id).where(BookingKey.id==booking.asset_key))
    if booking.status=='cancelled':return dto(booking,asset)
    if booking.version!=expected_version:raise Conflict('Stale booking version')
    booking.status='cancelled';booking.version+=1;session.flush()
    session.add(AuditEvent(actor_id=actor_id,asset_id=asset,department_id=booking.department_id,target_type='preventive_booking',target_id=booking.id,
        action='preventive_slot_cancelled',payload={'version':booking.version}));session.flush()
    return dto(booking,asset)

class ScheduleInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    asset_id:UUID
    start:datetime
    end:datetime
    reason:str=Field(min_length=1,max_length=500)
    request_key:UUID
class CancelInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    expected_version:int=Field(ge=1,strict=True)

def create_booking_app(factory,authenticate):
    app=FastAPI(title='Optional preventive slot prototype');bearer=HTTPBearer(auto_error=False)
    def identity(credentials:HTTPAuthorizationCredentials|None=Depends(bearer)):
        actor=authenticate(credentials.credentials) if credentials else None
        if actor is None:raise HTTPException(401,'Authentication required')
        return actor
    @app.exception_handler(PermissionError)
    def permission(request,error):return JSONResponse(status_code=403,content={'detail':'Permission denied'})
    @app.exception_handler(LookupError)
    def missing(request,error):return JSONResponse(status_code=404,content={'detail':'Resource unavailable'})
    @app.exception_handler(Conflict)
    def conflict(request,error):return JSONResponse(status_code=409,content={'detail':str(error)})
    @app.exception_handler(ValueError)
    def invalid(request,error):return JSONResponse(status_code=400,content={'detail':str(error)})
    @app.exception_handler(IntegrityError)
    def integrity(request,error):return JSONResponse(status_code=409 if error.orig.sqlstate=='23P01' else 400,content={'detail':'Slot overlaps or violates integrity'})
    @app.post('/bookings')
    def post(body:ScheduleInput,actor=Depends(identity)):
        with factory() as s,s.begin():result,created=schedule(s,actor,**body.model_dump())
        return JSONResponse(status_code=201 if created else 200,content=result)
    @app.post('/bookings/{booking_id}/cancel')
    def remove(booking_id:UUID,body:CancelInput,actor=Depends(identity)):
        with factory() as s,s.begin():return cancel(s,actor,booking_id,body.expected_version)
    @app.get('/bookings')
    def listing(limit:int=Query(20,ge=1,le=100),actor=Depends(identity)):
        with factory() as s,s.begin():
            scope=administrator(s,actor)
            query=select(Booking,BookingKey.asset_id).join(BookingKey).order_by(Booking.id).limit(limit)
            if scope.role!='super_admin':query=query.where(Booking.department_id==scope.department_id)
            return [dto(row[0],row[1]) for row in s.execute(query)]
    return app
