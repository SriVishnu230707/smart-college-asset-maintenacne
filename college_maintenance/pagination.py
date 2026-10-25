"""Bounded newest-first offset/keyset reads; cursors never confer access."""
import base64
import binascii
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import and_, or_
from college_maintenance.models import MaintenanceTicket
from college_maintenance.reads import TicketView, ticket_query, ticket_rows

@dataclass(frozen=True)
class TicketPage:
    items:tuple[TicketView,...]
    next_cursor:str | None

def _validate(limit,sort):
    if type(limit) is not int or not 1<=limit<=100:raise ValueError('limit must be an integer from 1 to 100')
    if sort!='newest':raise ValueError('Only newest created_at/id ordering is supported')

def _binding(scope,filters):
    value={'actor':str(scope.user_id),'role':scope.role,'department':str(scope.department_id),**{k:str(v) if v is not None else None for k,v in filters.items()}}
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def _encode(row,binding):
    value={'v':1,'at':row.created_at.astimezone(timezone.utc).isoformat(),'id':str(row.id),'bind':binding}
    return base64.urlsafe_b64encode(json.dumps(value,separators=(',',':')).encode()).decode().rstrip('=')

def _decode(cursor,binding):
    try:
        if not isinstance(cursor,str) or not 1<=len(cursor)<=2048:raise ValueError()
        value=json.loads(base64.b64decode(cursor.encode('ascii')+b'='*(-len(cursor)%4),altchars=b'-_',validate=True))
        if not isinstance(value,dict) or set(value)!={'v','at','id','bind'}:raise ValueError()
        if not all(isinstance(value[key],str) for key in ('at','id','bind')):raise ValueError()
        if type(value['v']) is not int or value['v']!=1 or value['bind']!=binding:raise ValueError()
        instant=datetime.fromisoformat(value['at'])
        if instant.tzinfo is None or instant.utcoffset() is None:raise ValueError()
        return instant.astimezone(timezone.utc),UUID(value['id'])
    except (ValueError,TypeError,KeyError,UnicodeError,binascii.Error,OverflowError):
        raise ValueError('Invalid cursor or cursor scope/filter mismatch') from None

def ticket_feed(session,scope,*,limit=20,cursor=None,department_id=None,status=None,priority=None,sort='newest'):
    _validate(limit,sort)
    filters=dict(department_id=department_id,status=status,priority=priority,sort=sort)
    binding=_binding(scope,filters)
    query=ticket_query(scope,department_id=department_id,status=status,priority=priority)
    if cursor is not None:
        instant,id=_decode(cursor,binding)
        query=query.where(or_(MaintenanceTicket.created_at<instant,and_(MaintenanceTicket.created_at==instant,MaintenanceTicket.id<id)))
    rows=ticket_rows(session,query.order_by(MaintenanceTicket.created_at.desc(),MaintenanceTicket.id.desc()).limit(limit+1))
    items=tuple(rows[:limit])
    return TicketPage(items,_encode(items[-1],binding) if len(rows)>limit else None)

def offset_feed(session,scope,*,offset=0,limit=20,department_id=None,status=None,priority=None,sort='newest'):
    _validate(limit,sort)
    if type(offset) is not int or not 0<=offset<=100000:raise ValueError('offset must be an integer from 0 to 100000')
    query=ticket_query(scope,department_id=department_id,status=status,priority=priority)
    return tuple(ticket_rows(session,query.order_by(MaintenanceTicket.created_at.desc(),MaintenanceTicket.id.desc()).offset(offset).limit(limit)))
