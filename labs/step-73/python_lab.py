from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import event,select,func,text
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column,Session
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed
from labs.shared.extensions_lab import extra_tables

class Mapping(DeclarativeBase):pass
class AssetEventExample(Mapping):
    __tablename__='event_assets'
    id:Mapped[int]=mapped_column(primary_key=True)
    name:Mapped[str]
class ORMLog(Mapping):
    __tablename__='event_orm_audit'
    id:Mapped[int]=mapped_column(primary_key=True)
    asset_id:Mapped[int]
    actor:Mapped[str]
class DatabaseLog(Mapping):
    __tablename__='event_database_audit'
    id:Mapped[int]=mapped_column(primary_key=True)
    asset_id:Mapped[int]
    actor:Mapped[str]

def scenario(lab):
    seed(lab);installed=False
    def before_flush(session,context,instances):
        for obj in list(session.new)+list(session.dirty):
            if isinstance(obj,AssetEventExample) and (obj in session.new or session.is_modified(obj)):
                session.add(ORMLog(asset_id=obj.id,actor=session.info.get('actor','unknown')))
    try:
        with extra_tables(lab,Mapping.metadata):
            with lab.engine.begin() as c:
                c.exec_driver_sql(f'''CREATE FUNCTION {lab.schema}.record_event() RETURNS trigger LANGUAGE plpgsql AS $$
                    BEGIN INSERT INTO {lab.schema}.event_database_audit(asset_id,actor)
                    VALUES(NEW.id,coalesce(nullif(current_setting('college.actor',true),''),'unknown')); RETURN NEW; END $$''')
                c.exec_driver_sql(f'CREATE TRIGGER event_audit AFTER INSERT OR UPDATE ON {lab.schema}.event_assets FOR EACH ROW EXECUTE FUNCTION {lab.schema}.record_event()')
                c.exec_driver_sql(f"CREATE FUNCTION {lab.schema}.canonical_code(value text) RETURNS text LANGUAGE sql IMMUTABLE STRICT AS $$ SELECT upper(btrim(value)) $$")
            event.listen(Session,'before_flush',before_flush);installed=True
            with lab.session() as s,s.begin():
                s.info['actor']='synthetic_admin';s.execute(text("SELECT set_config('college.actor','synthetic_admin',true)"))
                s.add(AssetEventExample(id=1,name='Original'))
            with lab.session() as s:
                check(s.scalar(select(func.count()).select_from(ORMLog))==s.scalar(select(func.count()).select_from(DatabaseLog))==1,'An ORM insert reaches both deliberately separate comparison mechanisms.')
                check(s.scalar(select(DatabaseLog.actor))=='synthetic_admin','A trusted transaction-local application actor reaches the database trigger.')
                check(s.scalar(select(getattr(func,lab.schema).canonical_code(' lab ')))=='LAB','A stored SQL function is callable through the schema-qualified SQLAlchemy func namespace.')
            lab.driver().execute(f"UPDATE {lab.schema}.event_assets SET name='Direct SQL' WHERE id=1")
            with lab.session() as s:
                check(s.scalar(select(func.count()).select_from(ORMLog))==1 and s.scalar(select(func.count()).select_from(DatabaseLog))==2,'Direct SQL bypasses ORM events while the database trigger still records the write.')
                check(s.scalar(select(DatabaseLog.actor).order_by(DatabaseLog.id.desc()).limit(1))=='unknown','A missing trusted application actor is labeled unknown rather than invented from the shared database login.')
            event.remove(Session,'before_flush',before_flush);installed=False
            with lab.session() as s,s.begin():s.get(AssetEventExample,1).name='Database-only authority'
            try:
                with lab.session() as s,s.begin():
                    obj=s.get(AssetEventExample,1);obj.name='Rolled back';s.flush();raise RuntimeError('injected')
            except RuntimeError:pass
            with lab.session() as s:
                check(s.scalar(select(func.count()).select_from(DatabaseLog))==3,'Trigger audit writes roll back with a failed business transaction.')
                check(s.scalar(select(func.count()).select_from(ORMLog))==1,'After selecting database auditing as authority, later writes do not double-log through ORM hooks.')
            check(lab.driver().execute(f'SELECT name FROM {lab.schema}.event_assets').fetchone()[0]=='Database-only authority','An independent connection confirms rollback preserved the last committed fact.')
    finally:
        if installed:event.remove(Session,'before_flush',before_flush)
        with lab.engine.begin() as c:
            c.exec_driver_sql(f'DROP FUNCTION IF EXISTS {lab.schema}.record_event()')
            c.exec_driver_sql(f'DROP FUNCTION IF EXISTS {lab.schema}.canonical_code(text)')
    print('Audit tables are not automatically tamper-proof. Use trusted actor propagation, one authoritative mechanism, protected privileges and explicit coverage for every writer.')

if __name__=='__main__':run(73,scenario)
