from pathlib import Path
from decimal import Decimal
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import select,func,Numeric,inspect
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,column_property,load_only
from college_maintenance.models import MaintenanceTicket,WorkOrder,SparePart,WorkOrderPart
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed
from labs.shared.extensions_lab import extra_tables

class Mapping(DeclarativeBase):pass
class Estimate(Mapping):
    __tablename__='derived_estimates'
    id:Mapped[int]=mapped_column(primary_key=True)
    quantity:Mapped[int]=mapped_column()
    unit_cost:Mapped[Decimal]=mapped_column(Numeric(12,2))
    total=column_property(quantity*unit_cost)

def scenario(lab):
    ids=seed(lab)
    with lab.session() as s,s.begin():
        ticket=MaintenanceTicket(asset_id=ids['asset'],department_id=ids['dept'],reported_by_id=ids['reporter'],title='Derived cost',description='Synthetic example',priority='low')
        order=WorkOrder(ticket=ticket,technician_id=ids['tech'])
        part=SparePart(sku='HYBRID',name='Example',current_unit_cost=Decimal('2.50'))
        usage=WorkOrderPart(work_order=order,part=part,quantity_used=4,unit_cost_at_use=Decimal('2.50'));s.add(usage);s.flush();order_id=order.id;part_id=part.id
        check(usage.line_total==Decimal('10.00'),'A hybrid evaluates exact Decimal arithmetic on a Python instance.')
    with lab.session() as s:
        lab.statements.clear()
        total=s.scalar(select(func.sum(WorkOrderPart.line_total)))
        check(total==10 and len(lab.statements)==1,'The same hybrid composes into one SQL aggregate without loading a collection.')
        check(s.scalars(select(WorkOrderPart.work_order_id).where(WorkOrderPart.line_total>9)).all()==[order_id],'A hybrid expression can participate in SQL filtering.')
    with lab.session() as s:
        obj=s.scalar(select(WorkOrderPart).options(load_only(WorkOrderPart.quantity_used)))
        check('unit_cost_at_use' in inspect(obj).unloaded,'A deliberate deferred cost column is visible in object loading state.')
        lab.statements.clear();value=obj.line_total
        check(value==10 and len(lab.statements)==1,'Instance evaluation can trigger deferred-column I/O; a plain property is not automatically a free query.')
    with extra_tables(lab,Mapping.metadata):
        with lab.session() as s,s.begin():s.add(Estimate(id=1,quantity=3,unit_cost=Decimal('2.00')))
        with lab.session() as s:check(s.get(Estimate,1).total==6,'column_property loads a database-computed projection alongside the mapped row.')
        check('total' not in Estimate.__table__.c,'A mapped SQL-expression property does not add a stored database column.')
    check(len(WorkOrderPart.__table__.columns)==4,'Promoting line_total to a hybrid changes no installed application columns or migration history.')

if __name__=='__main__':run(69,scenario)
