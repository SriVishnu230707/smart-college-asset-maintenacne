"""Controlled independent Sessions; the one-slot application pool stays unchanged."""
from contextlib import contextmanager
import time
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from college_maintenance.database import engine

@contextmanager
def independent_factory(lab):
    target=create_engine(engine.url,poolclass=NullPool,hide_parameters=True,connect_args={
        'connect_timeout':5,'options':'-c timezone=UTC -c statement_timeout=8000 -c lock_timeout=6000'})
    try:yield sessionmaker(bind=target.execution_options(schema_translate_map={None:lab.schema}))
    finally:target.dispose()

def wait_blocked(observer,blocked,blocker,timeout=3):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        # A later tuple-lock waiter can depend on an earlier waiter. Follow
        # the observed wait graph rather than assuming every edge is direct.
        if observer.execute('''WITH RECURSIVE blockers(pid) AS (
            SELECT unnest(pg_blocking_pids(%s)) UNION
            SELECT unnest(pg_blocking_pids(pid)) FROM blockers)
            SELECT EXISTS(SELECT 1 FROM blockers WHERE pid=%s)''',(blocked,blocker)).fetchone()[0]:return True
        time.sleep(0.02)
    return False
