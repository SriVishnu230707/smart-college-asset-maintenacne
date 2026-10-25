"""Balance-plus-ledger operations; all helpers participate in an outer transaction."""
from decimal import Decimal, InvalidOperation
from sqlalchemy import select, func, update
from college_maintenance.models import SparePart, Supplier, InventoryMovement
from college_maintenance.reads import scope_for_actor
from college_maintenance.workflow import Conflict, NotFound, nonblank
from college_maintenance.auditing import audit_change

MAX_MONEY = Decimal('9999999999.99')

def money(value):
    try:
        if isinstance(value,(float,bool)): raise ValueError('Money must be exact')
        amount=Decimal(value)
        if not amount.is_finite() or amount.as_tuple().exponent < -2 or not 0 <= amount <= MAX_MONEY:
            raise ValueError('Money must have at most two decimals within numeric(12,2)')
        return amount.quantize(Decimal('0.01'))
    except (InvalidOperation,TypeError): raise ValueError('Invalid exact monetary value') from None

def quantity(value, allow_zero=False):
    if type(value) is not int or not (0 if allow_zero else 1) <= value <= 2147483647:
        raise ValueError('Quantity must be a bounded whole number')
    return value

def inventory_admin(session, actor_id):
    actor=scope_for_actor(session,actor_id)
    if actor.role != 'super_admin': raise PermissionError('Central inventory requires Super Admin')
    return actor

def add_supplier(session, actor_id, name, contact, request_id=None):
    inventory_admin(session,actor_id)
    row=Supplier(name=nonblank(name,'supplier name',150),contact=nonblank(contact,'supplier contact',1000))
    session.add(row);session.flush()
    audit_change(session,actor_id,'supplier_created',target_type='supplier',target_id=row.id,request_id=request_id)
    return dict(id=row.id,name=row.name,contact=row.contact)

def create_part(session, actor_id, *, sku, name, unit_cost, opening=0, reorder_level=0, request_id=None):
    inventory_admin(session,actor_id); quantity(opening,True);quantity(reorder_level,True)
    part=SparePart(sku=nonblank(sku,'SKU',50).upper(),name=nonblank(name,'part name',150),current_unit_cost=money(unit_cost),stock_quantity=opening,reorder_level=reorder_level)
    session.add(part);session.flush()
    if opening: session.add(InventoryMovement(spare_part_id=part.id,actor_id=actor_id,kind='opening',quantity_delta=opening))
    audit_change(session,actor_id,'part_created',target_type='part',target_id=part.id,request_id=request_id,details={'opening':opening})
    return part

def move_stock(session, actor_id, part_id, *, kind, delta, supplier_id=None, reason=None, request_id=None):
    inventory_admin(session,actor_id)
    if type(delta) is not int or delta == 0 or abs(delta)>2147483647: raise ValueError('Invalid movement quantity')
    part=session.scalar(select(SparePart).where(SparePart.id==part_id).with_for_update().execution_options(populate_existing=True))
    if part is None: raise NotFound('Part not found')
    if part.is_archived: raise Conflict('Archived part cannot receive stock changes')
    if kind=='receipt':
        supplier=session.get(Supplier,supplier_id) if supplier_id else None
        if delta<0 or supplier is None or supplier.is_archived: raise ValueError('A receipt needs positive quantity and an active supplier')
    elif kind=='adjustment':
        if supplier_id is not None: raise ValueError('Adjustment cannot name a supplier')
        reason=nonblank(reason,'adjustment reason',10000)
    else: raise ValueError('Only receipts and adjustments are inventory commands')
    balance=part.stock_quantity+delta
    if not 0<=balance<=2147483647: raise Conflict('Movement would leave an invalid stock balance')
    part.stock_quantity=balance;session.flush()
    movement=InventoryMovement(spare_part_id=part.id,actor_id=actor_id,kind=kind,quantity_delta=delta,supplier_id=supplier_id,reason=reason)
    session.add(movement)
    audit_change(session,actor_id,'stock_'+kind,target_type='part',target_id=part.id,request_id=request_id,details={'delta':delta,'balance':balance,'reason':reason})
    return part

def part_result(part):
    return dict(id=part.id,sku=part.sku,name=part.name,stock_quantity=part.stock_quantity,reorder_level=part.reorder_level,
        current_unit_cost=format(part.current_unit_cost,'.2f'),is_archived=part.is_archived)

def reconciliation_query():
    totals=select(InventoryMovement.spare_part_id,func.sum(InventoryMovement.quantity_delta).label('ledger_balance')).group_by(InventoryMovement.spare_part_id).subquery()
    return select(SparePart.id,SparePart.stock_quantity,func.coalesce(totals.c.ledger_balance,0).label('ledger_balance')).outerjoin(totals,totals.c.spare_part_id==SparePart.id).order_by(SparePart.id)

def guarded_stock_statement(part_id,amount):
    quantity(amount)
    return (update(SparePart).where(SparePart.id==part_id,SparePart.stock_quantity>=amount,SparePart.is_archived.is_(False))
        .values(stock_quantity=SparePart.stock_quantity-amount)
        .returning(SparePart.current_unit_cost,SparePart.stock_quantity))

def consume_guarded(session,part_id,amount):
    """Persistence primitive; caller owns authorization, parent locks and ledger."""
    row=session.execute(guarded_stock_statement(part_id,amount).execution_options(synchronize_session=False)).one_or_none()
    if row is None:raise Conflict('Insufficient stock or unavailable part')
    return row.current_unit_cost
