from pathlib import Path
from dataclasses import dataclass,is_dataclass
from datetime import datetime
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import ForeignKey,DateTime,func,select
from sqlalchemy.orm import DeclarativeBase,Mapped,MappedAsDataclass,mapped_column,relationship,composite,selectinload
from sqlalchemy.ext.associationproxy import association_proxy
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed
from labs.shared.extensions_lab import extra_tables

class Mapping(DeclarativeBase):pass
class Timestamps:
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),server_default=func.now())
@dataclass(frozen=True)
class Location:
    building:str
    room:str
class Part(Mapping):
    __tablename__='helper_parts'
    id:Mapped[int]=mapped_column(primary_key=True)
    name:Mapped[str]
class Order(Timestamps,Mapping):
    __tablename__='helper_orders'
    id:Mapped[int]=mapped_column(primary_key=True)
    building:Mapped[str]
    room:Mapped[str]
    location:Mapped[Location]=composite(Location,'building','room')
    lines:Mapped[list['Line']]=relationship(back_populates='order')
    parts=association_proxy('lines','part')
    parts_view:Mapped[list[Part]]=relationship(secondary='helper_lines',viewonly=True)
class Line(Mapping):
    __tablename__='helper_lines'
    order_id:Mapped[int]=mapped_column(ForeignKey('helper_orders.id'),primary_key=True)
    part_id:Mapped[int]=mapped_column(ForeignKey('helper_parts.id'),primary_key=True)
    quantity:Mapped[int]
    order:Mapped[Order]=relationship(back_populates='lines')
    part:Mapped[Part]=relationship()
class DataclassMapping(MappedAsDataclass,DeclarativeBase):pass
class DataclassItem(DataclassMapping):
    __tablename__='helper_dataclass_items'
    id:Mapped[int]=mapped_column(init=False,primary_key=True)
    label:Mapped[str]

def scenario(lab):
    seed(lab)
    with extra_tables(lab,Mapping.metadata),extra_tables(lab,DataclassMapping.metadata):
        with lab.session() as s,s.begin():
            order=Order(id=1,location=Location('Engineering','101'))
            part=Part(id=1,name='Fuse');s.add_all([Line(order=order,part=part,quantity=2),Part(id=2,name='Unused')])
            item=DataclassItem(label='Dataclass part');s.add(item);s.flush()
            check(order.created_at.tzinfo is not None,'A reusable timestamp mixin loads an aware server-generated event time.')
            check(order.building=='Engineering' and order.room=='101','A composite value object maps explicitly to two relational columns.')
            check(is_dataclass(item) and item.id is not None,'Mapped dataclass construction and database-generated identity work together.')
        with lab.session() as s,s.begin():
            lab.statements.clear()
            order=s.scalar(select(Order).options(selectinload(Order.lines).joinedload(Line.part),selectinload(Order.parts_view)))
            check(order.parts[0].name=='Fuse' and len(lab.statements)==3,'An association proxy reads through explicitly loaded authoritative usage rows without extra SQL.')
            order.parts_view.append(s.get(Part,2));s.flush()
            check(s.scalar(select(func.count()).select_from(Line))==1,'Mutating a viewonly convenience collection does not create a second writable association path.')
            order.location=Location('Engineering','202')
        with lab.session() as s:
            order=s.get(Order,1)
            check(order.location==Location('Engineering','202'),'Replacing the immutable composite persists both intended value components.')
            check([part.id for part in order.parts_view]==[1],'A fresh Session reloads the real viewonly relationship, ignoring unpersisted list edits.')
        try:DataclassItem(id=99,label='Invalid constructor')
        except TypeError:check(True,'init=False keeps generated IDs out of the dataclass constructor contract.')
        else:raise AssertionError('Generated identity accepted by constructor')
    check(lab.driver().execute('SELECT to_regclass(%s)',(lab.schema+'.helper_lines',)).fetchone()[0] is None,'Mapping conveniences leave no extra production tables or alternate persistence route.')

if __name__=='__main__':run(70,scenario)
