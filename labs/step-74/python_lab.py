from pathlib import Path
from uuid import UUID
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import ForeignKey,create_engine,text
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column
from sqlalchemy.exc import DBAPIError
from college_maintenance.models import Department
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed
from labs.shared.extensions_lab import extra_tables
from labs.shared.operations_lab import runtime_role,admin_connection

class Mapping(DeclarativeBase):pass
class DepartmentNote(Mapping):
    __tablename__='department_notes'
    id:Mapped[int]=mapped_column(primary_key=True)
    department_id:Mapped[UUID]=mapped_column(ForeignKey(Department.id))
    body:Mapped[str]

def scenario(lab):
    ids=seed(lab)
    with extra_tables(lab,Mapping.metadata):
        with lab.session() as s,s.begin():s.add_all([DepartmentNote(id=1,department_id=ids['dept'],body='A'),DepartmentNote(id=2,department_id=ids['other_dept'],body='B')])
        with lab.engine.begin() as c:
            c.exec_driver_sql(f'ALTER TABLE {lab.schema}.department_notes ENABLE ROW LEVEL SECURITY')
            c.exec_driver_sql(f'ALTER TABLE {lab.schema}.department_notes FORCE ROW LEVEL SECURITY')
            predicate="department_id=nullif(current_setting('college.department',true),'')::uuid"
            c.exec_driver_sql(f'CREATE POLICY department_policy ON {lab.schema}.department_notes USING ({predicate}) WITH CHECK ({predicate})')
        with runtime_role(lab) as url:
            runtime=create_engine(url,pool_size=1,max_overflow=0,hide_parameters=True)
            try:
                with runtime.begin() as c:check(c.exec_driver_sql(f'SELECT count(*) FROM {lab.schema}.department_notes').scalar_one()==0,'An actual non-owner login without request context receives no RLS rows.')
                with runtime.begin() as c:
                    c.execute(text("SELECT set_config('college.department',:dept,true)"),{'dept':str(ids['dept'])})
                    check(c.exec_driver_sql(f'SELECT body FROM {lab.schema}.department_notes').scalars().all()==['A'],'USING restricts reads to the server-supplied transaction-local department.')
                    c.exec_driver_sql(f'INSERT INTO {lab.schema}.department_notes VALUES (%s,%s,%s)',(3,ids['dept'],'Own insert'))
                    check(c.exec_driver_sql(f'UPDATE {lab.schema}.department_notes SET body=%s WHERE id=2',('Hidden edit',)).rowcount==0,'Rows outside scope cannot be selected for UPDATE.')
                    for statement,params in [(f'UPDATE {lab.schema}.department_notes SET department_id=%s WHERE id=1',(ids['other_dept'],)),(f'INSERT INTO {lab.schema}.department_notes VALUES(4,%s,%s)',(ids['other_dept'],'Forbidden'))]:
                        try:
                            with c.begin_nested():c.exec_driver_sql(statement,params)
                        except DBAPIError as exc:check(exc.orig.sqlstate=='42501','WITH CHECK rejects inserts or updates that move a row outside authorized context.')
                        else:raise AssertionError('RLS check bypass')
                with runtime.begin() as c:check(c.exec_driver_sql(f'SELECT count(*) FROM {lab.schema}.department_notes').scalar_one()==0,'Transaction-local context does not leak through the reused one-slot connection pool.')
                try:
                    with runtime.begin() as c:c.exec_driver_sql(f'ALTER TABLE {lab.schema}.department_notes DISABLE ROW LEVEL SECURITY')
                except DBAPIError as exc:check(exc.orig.sqlstate=='42501','The limited runtime login cannot disable the owner-installed policy.')
                else:raise AssertionError('Runtime disabled RLS')
            finally:runtime.dispose()
        check(lab.driver().execute(f'SELECT count(*) FROM {lab.schema}.department_notes').fetchone()[0]==0,'FORCE RLS also constrains the ordinary table owner when no context is set.')
        with admin_connection('college_learning') as admin:check(admin.execute(f'SELECT count(*) FROM {lab.schema}.department_notes').fetchone()[0]==3,'A superuser still bypasses FORCE RLS; the proof deliberately tests the non-owner runtime instead.')
    print('Trust boundary: the application derives context from authenticated identity. Anyone holding the shared runtime SQL credential can set a different context; GUC-based RLS is not protection against arbitrary SQL access by that account.')

if __name__=='__main__':run(74,scenario)
