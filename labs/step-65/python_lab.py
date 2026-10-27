from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import select,func,text
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed
from labs.shared.extensions_lab import extra_tables
from labs.shared.performance_lab import explain,nodes,save_plans

class Mapping(DeclarativeBase):pass
class Specification(Mapping):
    __tablename__='specification_examples'
    id:Mapped[int]=mapped_column(primary_key=True)
    specs:Mapped[dict|None]=mapped_column(MutableDict.as_mutable(JSONB(none_as_null=True)))

def scenario(lab):
    seed(lab)
    with extra_tables(lab,Mapping.metadata):
        with lab.session() as s,s.begin():s.add(Specification(id=1,specs={'ram':8,'nested':{'cpu':'original'}}))
        with lab.session() as s,s.begin():
            obj=s.get(Specification,1)
            obj.specs['ram']=16
        with lab.session() as s,s.begin():
            obj=s.get(Specification,1);check(obj.specs['ram']==16,'MutableDict persists top-level in-place changes through a fresh Session.')
            obj.specs['nested']['cpu']='not tracked'
        with lab.session() as s,s.begin():
            obj=s.get(Specification,1);check(obj.specs['nested']['cpu']=='original','Nested dictionaries are not recursively tracked by plain MutableDict.')
            obj.specs={**obj.specs,'nested':{'cpu':'reassigned'}}
        with lab.session() as s:check(s.get(Specification,1).specs['nested']['cpu']=='reassigned','Explicit replacement persists a deliberate nested change.')
        with lab.engine.begin() as c:
            c.exec_driver_sql(f"INSERT INTO {lab.schema}.specification_examples VALUES (3,'null'::jsonb),(4,NULL)")
            c.exec_driver_sql(f"INSERT INTO {lab.schema}.specification_examples SELECT i+100,jsonb_build_object('ram',CASE WHEN i%%500=0 THEN 16 ELSE 8 END) FROM generate_series(1,20000) i")
            c.exec_driver_sql(f'CREATE INDEX specifications_gin ON {lab.schema}.specification_examples USING gin(specs jsonb_path_ops)')
            c.exec_driver_sql(f'ANALYZE {lab.schema}.specification_examples')
            plan=explain(c,f'SELECT id FROM {lab.schema}.specification_examples WHERE specs @> %s::jsonb',('{"ram":16}',))
            check(any(n.get('Index Name')=='specifications_gin' for n in nodes(plan['Plan'])),'Measured selective containment uses a justified jsonb_path_ops GIN index.')
            save_plans(65,json_containment=plan)
        with lab.session() as s:
            check(s.scalar(select(func.count()).select_from(Specification).where(Specification.specs.contains({'ram':16})))==41,'Typed SQLAlchemy containment agrees with the generated selective fixture.')
            check(s.scalars(select(Specification.id).where(Specification.specs.is_(None))).all()==[4],'SQL NULL is identified by IS NULL independently of JSON null.')
            check(s.scalars(select(Specification.id).where(func.jsonb_typeof(Specification.specs)=='null')).all()==[3],'JSON null remains a JSON value distinguishable using jsonb_typeof.')
    check(lab.driver().execute('SELECT to_regclass(%s)',(lab.schema+'.specification_examples',)).fetchone()[0] is None,'Specialist mapping and index are removed without altering application migrations.')

if __name__=='__main__':run(65,scenario)
