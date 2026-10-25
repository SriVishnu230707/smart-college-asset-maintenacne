"""Disposable databases for migration proofs; no factory reset or volume removal."""
from contextlib import contextmanager
from pathlib import Path
import re
import psycopg
from psycopg import sql
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
from college_maintenance.database import engine

@contextmanager
def temporary_database(step, run_id):
    name=f'college_step{step}_{run_id.hex}'
    assert re.fullmatch(r'college_step(26|27)_[0-9a-f]{32}',name)
    args=engine.url.translate_connect_args(username='user',database='dbname')
    args.update(user='postgres',dbname='postgres',password=(Path(__file__).resolve().parents[2]/'.local/postgres-admin-password').read_text().strip())
    admin=psycopg.connect(**args,autocommit=True,connect_timeout=5)
    created=False
    target=None
    try:
        admin.execute(sql.SQL('CREATE DATABASE {} OWNER {}').format(sql.Identifier(name),sql.Identifier('college_learner')))
        created=True
        target=create_engine(engine.url.set(database=name),poolclass=NullPool,hide_parameters=True,connect_args={'connect_timeout':5,'options':'-c timezone=UTC'})
        yield target
    finally:
        try:
            if target is not None:target.dispose()
            if created:admin.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
        finally:
            admin.close()
