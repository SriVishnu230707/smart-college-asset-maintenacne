"""Strictly generated operational resources; credentials never leave ignored storage."""
from contextlib import contextmanager
from pathlib import Path
import re,secrets
import psycopg
from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from college_maintenance.database import engine

def admin_connection(database='postgres'):
    args=engine.url.translate_connect_args(username='user',database='dbname')
    args.update(user='postgres',dbname=database,password=(Path(__file__).resolve().parents[2]/'.local/postgres-admin-password').read_text().strip())
    return psycopg.connect(**args,autocommit=True,connect_timeout=5)

@contextmanager
def scratch_database(step,run_id):
    name=f'college_ops{step}_{run_id.hex}'
    assert re.fullmatch(r'college_ops(?:5[8-9]|[6-7][0-9]|80)_[0-9a-f]{32}',name)
    with admin_connection() as admin:
        admin.execute(sql.SQL('CREATE DATABASE {} OWNER college_learner').format(sql.Identifier(name)))
        target=create_engine(engine.url.set(database=name),poolclass=NullPool,hide_parameters=True,connect_args={'connect_timeout':5})
        try:yield target
        finally:
            target.dispose()
            admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))

@contextmanager
def runtime_role(lab):
    role=f'college_runtime_{lab.run_id.hex}';password=secrets.token_urlsafe(32)
    with admin_connection() as admin:
        admin.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT').format(sql.Identifier(role),sql.Literal(password)))
        connection=lab.driver()
        try:
            connection.execute(sql.SQL('GRANT USAGE ON SCHEMA {} TO {}').format(sql.Identifier(lab.schema),sql.Identifier(role)))
            connection.execute(sql.SQL('GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA {} TO {}').format(sql.Identifier(lab.schema),sql.Identifier(role)))
            yield engine.url.set(username=role,password=password)
        finally:
            # Grants exist only in this database; no FORCE/drop-owned-object reset.
            connection.execute(sql.SQL('REVOKE ALL ON ALL TABLES IN SCHEMA {} FROM {}').format(sql.Identifier(lab.schema),sql.Identifier(role)))
            connection.execute(sql.SQL('REVOKE ALL ON SCHEMA {} FROM {}').format(sql.Identifier(lab.schema),sql.Identifier(role)))
            admin.execute(sql.SQL('DROP ROLE {}').format(sql.Identifier(role)))
