from pathlib import Path
from dataclasses import dataclass
import re,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import String,CheckConstraint,select,cast
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,validates
from sqlalchemy.exc import StatementError,IntegrityError
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed
from labs.shared.extensions_lab import extra_tables

@dataclass(frozen=True)
class Code:
    value:str
class CodeType(TypeDecorator):
    impl=String(50)
    cache_ok=True  # fixed, hashable type configuration; no external mutable state
    def process_bind_param(self,value,dialect):
        if value is None:return None
        value=value.value if isinstance(value,Code) else value
        if not isinstance(value,str):raise ValueError('Code must be text')
        value=value.strip().upper()
        if not re.fullmatch(r'[A-Z0-9-]{1,50}',value):raise ValueError('Invalid code')
        return value
    def process_result_value(self,value,dialect):return None if value is None else Code(value)
    class comparator_factory(TypeDecorator.Comparator):
        def has_prefix(self,prefix):
            return cast(self.expr,String).startswith(prefix.upper(),autoescape=True)
class Mapping(DeclarativeBase):pass
class Item(Mapping):
    __tablename__='custom_code_examples'
    __table_args__=(CheckConstraint("code ~ '^[A-Z0-9-]{1,50}$'"),)
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[Code]=mapped_column(CodeType(),unique=True)
    label:Mapped[str]
    @validates('label')
    def validate_label(self,key,value):
        if not value.strip():raise ValueError('Blank Python label')
        return value.strip()

def scenario(lab):
    seed(lab)
    with extra_tables(lab,Mapping.metadata):
        with lab.session() as s,s.begin():s.add(Item(id=1,code=' ab-1 ',label=' Example '))
        with lab.session() as s:
            item=s.get(Item,1)
            check(item.code==Code('AB-1') and item.label=='Example','Custom bind/result conversion and attribute normalization round-trip through a fresh Session.')
            check(s.scalars(select(Item.id).where(Item.code==Code('AB-1'))).all()==[1],'Domain value objects can participate in bound comparisons.')
            check(s.scalars(select(Item.id).where(Item.code.has_prefix('ab'))).all()==[1],'A custom comparator composes a normal SQL expression.')
            check(s.scalars(select(Item.id).where(Item.code.has_prefix('%'))).all()==[],'Comparator prefix values escape wildcard syntax instead of interpolating SQL.')
        try:
            with lab.session() as s,s.begin():s.add(Item(id=2,code='INVALID!',label='Valid'))
        except StatementError as exc:check(isinstance(exc.orig,ValueError),'Invalid domain binding fails before a PostgreSQL INSERT is accepted.')
        else:raise AssertionError('Invalid code bound')
        try:Item(code='X',label=' ')
        except ValueError:check(True,'Attribute validation applies to ordinary Python assignments.')
        else:raise AssertionError('Invalid Python label')
        with lab.engine.begin() as c:
            try:
                with c.begin_nested():c.exec_driver_sql(f"INSERT INTO {lab.schema}.custom_code_examples VALUES(3,'lowercase','Bypass')")
            except IntegrityError:check(True,'Direct SQL bypasses Python conversion but the separate database CHECK still rejects invalid codes.')
            else:raise AssertionError('Database integrity absent')
            c.exec_driver_sql(f"INSERT INTO {lab.schema}.custom_code_examples VALUES(4,'RAW','')")
        check(lab.driver().execute(f'SELECT label FROM {lab.schema}.custom_code_examples WHERE id=4').fetchone()[0]=='','A deliberate raw-SQL blank label proves Python validators are not database constraints.')
    print('The deliberately weaker label rule exists only in this disposable lab. Production invariants need database constraints; cache_ok concerns statement compilation, not cached row values.')

if __name__=='__main__':run(72,scenario)
