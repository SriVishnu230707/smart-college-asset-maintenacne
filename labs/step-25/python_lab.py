"""Preserve application history; demonstrate ownership on disposable children."""
import sys
from decimal import Decimal
from pathlib import Path
from uuid import UUID
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import ForeignKey, Uuid, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from college_maintenance.models import Department, MaintenanceTicket, SparePart, WorkOrder, WorkOrderPart
from labs.shared.orm_lab import check, run

class DemoBase(DeclarativeBase): pass
class Parent(DemoBase):
    __tablename__='owned_parents'
    id:Mapped[UUID]=mapped_column(Uuid,primary_key=True,server_default=text('gen_random_uuid()'))
    children:Mapped[list['Child']]=relationship(back_populates='parent',cascade='all, delete-orphan',passive_deletes=True)
class Child(DemoBase):
    __tablename__='owned_children'
    id:Mapped[UUID]=mapped_column(Uuid,primary_key=True,server_default=text('gen_random_uuid()'))
    parent_id:Mapped[UUID]=mapped_column(ForeignKey('owned_parents.id',ondelete='CASCADE'))
    parent:Mapped[Parent]=relationship(back_populates='children')

def scenario(lab):
    ids=lab.seed()
    with lab.engine.begin() as c: DemoBase.metadata.create_all(c)
    with lab.session() as s,s.begin():
        parents=[Parent(children=[Child(),Child()]) for _ in range(3)]
        s.add_all(parents);s.flush()
        parent_ids=[p.id for p in parents]; child_ids=[[c.id for c in p.children] for p in parents]
    with lab.session() as s,s.begin():
        p=s.get(Parent,parent_ids[0]);orphan=p.children.pop();s.flush()
        check(inspect(orphan).deleted,'Removing a disposable owned child invokes delete-orphan on flush.')
        before=len(lab.kinds('owned_children'));s.delete(p);s.flush()
        check(lab.kinds('owned_children')[before:]==['DELETE'],'Loaded ownership deletion explicitly deletes the remaining child before its parent.')
    with lab.session() as s,s.begin():
        p=s.get(Parent,parent_ids[1]);check('children' in inspect(p).unloaded,'The second disposable parent begins with an unloaded collection.')
        before=len(lab.kinds('owned_children'));s.delete(p);s.flush()
        check(len(lab.kinds('owned_children'))==before,'Passive deletion of an unloaded parent emits no child SELECT or DELETE; PostgreSQL cascades it.')
    with lab.engine.begin() as c:c.execute(text(f'DELETE FROM {lab.schema}.owned_parents WHERE id=:id'),{'id':parent_ids[2]})
    with lab.session() as s:
        check(all(s.get(Child,id) is None for group in child_ids for id in group),'Direct SQL and both ORM loading paths leave no disposable owned children.')
    with lab.session() as s,s.begin():
        t=MaintenanceTicket(asset_id=ids['asset'],reported_by_id=ids['reporter'],department_id=ids['dept'],title='History',description='Retained references',priority='high')
        order=WorkOrder(ticket=t,technician_id=ids['tech'])
        part=SparePart(sku='KEEP-PART',name='Retained part',current_unit_cost=Decimal('1.25'))
        order.part_usages=[WorkOrderPart(part=part,quantity_used=1,unit_cost_at_use=Decimal('1.25'))]
        s.add(order);s.flush();ticket_id,order_id,part_id=t.id,order.id,part.id
    for model,id,collection in [(Department,ids['dept'],'assets'),(MaintenanceTicket,ticket_id,'work_orders'),(WorkOrder,order_id,'part_usages')]:
        for loaded in (False,True):
            try:
                with lab.session() as s,s.begin():
                    obj=s.get(model,id)
                    if loaded:list(getattr(obj,collection))
                    s.delete(obj);s.flush()
            except IntegrityError as exc:check(exc.orig.sqlstate=='23001',f'{model.__name__} deletion with loaded={loaded} reaches database RESTRICT without nulling history.')
            else:raise AssertionError('Referenced history was deleted')
    with lab.engine.begin() as c:
        try:
            with c.begin_nested():c.execute(text(f'DELETE FROM {lab.schema}.spare_parts WHERE id=:id'),{'id':part_id})
        except IntegrityError as exc:check(exc.orig.sqlstate=='23001','Direct SQL cannot delete a part referenced by historical cost lines.')
        else:raise AssertionError('Referenced part was deleted')
    with lab.session() as s:
        check(s.get(MaintenanceTicket,ticket_id) is not None and s.get(WorkOrderPart,(order_id,part_id)).unit_cost_at_use==Decimal('1.25'),
              'Ticket, work order, and cost snapshot remain intact after every failed deletion.')
    check(inspect(WorkOrder).relationships.part_usages.passive_deletes=='all'
          and not inspect(WorkOrder).relationships.part_usages.cascade.delete,'Application history uses database restriction, not ORM delete cascade or delete-orphan.')

if __name__=='__main__':run(25,scenario)
