from pathlib import Path
import os,sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import create_engine,text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.pool import NullPool
from college_maintenance.database import connection_url
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed
from labs.shared.operations_lab import runtime_role

def scenario(lab):
    ids=seed(lab)
    with runtime_role(lab) as url:
        runtime=create_engine(url,poolclass=NullPool,hide_parameters=True)
        try:
            with runtime.begin() as c:
                role=c.exec_driver_sql('SELECT current_user,rolsuper,rolcreatedb,rolcreaterole FROM pg_roles WHERE rolname=current_user').one()
                check(role[0]==url.username and role[1:]==(False,False,False),'A real LOGIN runtime role is neither owner nor administrative superuser.')
                c.exec_driver_sql(f'INSERT INTO {lab.schema}.assets(asset_code,name,department_id,category_id) VALUES (%s,%s,%s,%s)',('RUNTIME','Runtime asset',ids['dept'],ids['category']))
            for statement in [f'CREATE TABLE {lab.schema}.forbidden(id int)',f'ALTER TABLE {lab.schema}.assets ADD forbidden int',f'TRUNCATE {lab.schema}.assets','CREATE SCHEMA forbidden_schema']:
                try:
                    with runtime.begin() as c:c.exec_driver_sql(statement)
                except DBAPIError as exc:check(exc.orig.sqlstate=='42501','Runtime DML grants do not permit schema ownership, CREATE, ALTER or TRUNCATE.')
                else:raise AssertionError('Runtime DDL permitted')
            with tempfile.TemporaryDirectory(dir=Path('.local')) as directory:
                secret=Path(directory)/'database-url';secret.write_text(url.render_as_string(hide_password=False))
                previous=os.environ.get('COLLEGE_DATABASE_URL_FILE');os.environ['COLLEGE_DATABASE_URL_FILE']=str(secret)
                try:check(connection_url()==url,'Application connection configuration can read an ignored/mounted URL secret instead of owner credentials.')
                finally:
                    if previous is None:os.environ.pop('COLLEGE_DATABASE_URL_FILE')
                    else:os.environ['COLLEGE_DATABASE_URL_FILE']=previous
        finally:runtime.dispose()
    check(lab.driver().execute(f"SELECT count(*) FROM {lab.schema}.assets WHERE asset_code='RUNTIME'").fetchone()[0]==1,'Independent owner observation confirms the permitted runtime asset insert committed.')
    print('Trust boundary: this database account is the trusted application writer; business roles remain server-derived application identities. DML privileges alone are not per-row authorization.')

if __name__=='__main__':run(58,scenario)
