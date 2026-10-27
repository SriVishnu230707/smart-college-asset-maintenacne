"""Local bootstrap: administrative role provisioning, owner migrations, runtime grants."""
from pathlib import Path
from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from college_maintenance.database import engine
from college_maintenance.migrations import upgrade

def main():
    owner=make_url(Path('/run/secrets/owner_url').read_text().strip())
    runtime=make_url(Path('/run/secrets/runtime_url').read_text().strip())
    # Role passwords use psycopg's SQL literal quoting, never string interpolation.
    with engine.connect().execution_options(isolation_level='AUTOCOMMIT') as c:
        with c.connection.driver_connection.cursor() as cursor:
            for url in (owner,runtime):
                exists=cursor.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(url.username,)).fetchone()
                if not exists:cursor.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE').format(sql.Identifier(url.username),sql.Literal(url.password)))
            cursor.execute(sql.SQL('ALTER DATABASE college_deploy OWNER TO {}').format(sql.Identifier(owner.username)))
    migration_engine=create_engine(owner,hide_parameters=True)
    try:
        with migration_engine.begin() as c:
            upgrade(c)
            c.exec_driver_sql('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
            c.exec_driver_sql('GRANT USAGE ON SCHEMA public TO college_runtime')
            c.exec_driver_sql('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO college_runtime')
    finally:migration_engine.dispose();engine.dispose()
    print('Reviewed migrations applied as owner; runtime DML privileges installed. No credentials logged.')

if __name__=='__main__':main()
