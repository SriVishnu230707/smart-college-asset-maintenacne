from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import ForeignKey,select,func
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,selectin_polymorphic
from sqlalchemy.ext.declarative import ConcreteBase
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed
from labs.shared.extensions_lab import extra_tables

class Mapping(DeclarativeBase):pass
class SingleAsset(Mapping):
    __tablename__='single_assets'
    id:Mapped[int]=mapped_column(primary_key=True)
    name:Mapped[str]
    kind:Mapped[str]
    __mapper_args__={'polymorphic_on':'kind','polymorphic_identity':'asset'}
class SingleComputer(SingleAsset):
    ram:Mapped[int|None]=mapped_column(nullable=True)
    __mapper_args__={'polymorphic_identity':'computer'}
class SingleProjector(SingleAsset):
    lumens:Mapped[int|None]=mapped_column(nullable=True)
    __mapper_args__={'polymorphic_identity':'projector'}
class JoinedAsset(Mapping):
    __tablename__='joined_assets'
    id:Mapped[int]=mapped_column(primary_key=True)
    name:Mapped[str]
    kind:Mapped[str]
    __mapper_args__={'polymorphic_on':'kind','polymorphic_identity':'asset'}
class JoinedComputer(JoinedAsset):
    __tablename__='joined_computers'
    id:Mapped[int]=mapped_column(ForeignKey('joined_assets.id'),primary_key=True)
    ram:Mapped[int]
    __mapper_args__={'polymorphic_identity':'computer'}
class JoinedProjector(JoinedAsset):
    __tablename__='joined_projectors'
    id:Mapped[int]=mapped_column(ForeignKey('joined_assets.id'),primary_key=True)
    lumens:Mapped[int]
    __mapper_args__={'polymorphic_identity':'projector'}
class ConcreteAsset(ConcreteBase,Mapping):
    __tablename__='concrete_assets'
    _concrete_discriminator_name='_kind'
    id:Mapped[int]=mapped_column(primary_key=True)
    name:Mapped[str]
    __mapper_args__={'polymorphic_identity':'asset','concrete':True}
class ConcreteComputer(ConcreteAsset):
    __tablename__='concrete_computers'
    id:Mapped[int]=mapped_column(primary_key=True)
    name:Mapped[str]
    ram:Mapped[int]
    __mapper_args__={'polymorphic_identity':'computer','concrete':True}
class ConcreteProjector(ConcreteAsset):
    __tablename__='concrete_projectors'
    id:Mapped[int]=mapped_column(primary_key=True)
    name:Mapped[str]
    lumens:Mapped[int]
    __mapper_args__={'polymorphic_identity':'projector','concrete':True}

def scenario(lab):
    seed(lab)
    with extra_tables(lab,Mapping.metadata):
        with lab.session() as s,s.begin():
            for computer,projector in [(SingleComputer,SingleProjector),(JoinedComputer,JoinedProjector),(ConcreteComputer,ConcreteProjector)]:
                s.add_all([computer(id=1,name='Computer',ram=16),projector(id=2,name='Projector',lumens=3000)])
        with lab.session() as s:
            rows=s.scalars(select(SingleAsset).order_by(SingleAsset.id)).all()
            check(isinstance(rows[0],SingleComputer) and isinstance(rows[1],SingleProjector),'Single-table discrimination reconstructs the intended Python subtypes.')
            check(SingleAsset.__table__ is SingleComputer.__table__ and SingleAsset.__table__.c.ram.nullable,'Single-table subclass columns share one table and need deliberate nullable/subtype constraints.')
            lab.statements.clear()
            rows=s.scalars(select(JoinedAsset).options(selectin_polymorphic(JoinedAsset,[JoinedComputer,JoinedProjector]))).all()
            check(len(rows)==2 and len(lab.statements)==3,'Joined inheritance explicitly loads base rows and bounded subtype queries.')
            check(sum(getattr(row,'ram',0) for row in rows)==16,'Subclass-only values are available without unplanned per-instance lazy SQL.')
            rows=s.scalars(select(ConcreteAsset)).all()
            check({type(row) for row in rows}=={ConcreteComputer,ConcreteProjector},'Concrete inheritance queries a polymorphic union across independent subtype tables.')
            check('UNION ALL' in str(select(ConcreteAsset)),'The concrete base query exposes its union SQL cost rather than hiding the shape.')
            check(s.scalar(select(func.count()).select_from(JoinedAsset.__table__))==2 and s.scalar(select(func.count()).select_from(ConcreteAsset.__table__))==0,'Joined objects need base records; concrete objects do not insert a shared base row.')
    check(lab.driver().execute('SELECT to_regclass(%s)',(lab.schema+'.joined_assets',)).fetchone()[0] is None,'Alternative mappings remain isolated and leave the category-based application design unchanged.')
    print('Decision: keep categories/typed facts plus optional specifications in the base app; introduce inheritance only for stable subtype behavior that justifies schema, join and migration costs.')

if __name__=='__main__':run(71,scenario)
