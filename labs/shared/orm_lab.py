"""Committed, isolated ORM experiments with independently observed cleanup."""
import argparse
import json
from contextlib import contextmanager
from importlib.metadata import version
from uuid import UUID

import psycopg
from sqlalchemy import event, insert, text
from sqlalchemy.schema import CreateSchema

from college_maintenance.database import engine
from college_maintenance.models import Asset, AssetCategory, Base, Department, User
from college_maintenance.sessions import SessionFactory


def check(condition, message):
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


class Lab:
    def __init__(self, step, run_id):
        self.schema = f"college_step{step}"
        self.run_id = run_id
        self.engine = engine.execution_options(schema_translate_map={None: self.schema})
        self.sessions, self.drivers, self.statements = [], [], []

    def session(self, **options):
        session = SessionFactory(bind=self.engine, **options)
        self.sessions.append(session)
        return session

    def driver(self):
        connection = psycopg.connect(**engine.url.translate_connect_args(username="user", database="dbname"),
            autocommit=True, connect_timeout=5, options="-c statement_timeout=5000 -c timezone=UTC")
        self.drivers.append(connection)
        return connection

    def seed(self):
        with self.engine.begin() as c:
            def add(model, **values):
                return c.execute(insert(model.__table__).values(**values).returning(model.id)).scalar_one()
            dept = add(Department, code="CSE", name="Computer Science")
            other_dept = add(Department, code="ECE", name="Electronics")
            category = add(AssetCategory, code="COMPUTER", name="Computer")
            reporter = add(User, email="reporter@example.test", display_name="Reporter", password_hash="synthetic_phase_hash", role="student", department_id=dept)
            tech = add(User, email="tech@example.test", display_name="Technician", password_hash="synthetic_phase_hash", role="technician", department_id=dept)
            other = add(User, email="other@example.test", display_name="Other Reporter", password_hash="synthetic_phase_hash", role="student", department_id=other_dept)
            asset = add(Asset, asset_code="PC-001", name="Lab Computer", department_id=dept, category_id=category, location="Original Lab")
        return dict(dept=dept, other_dept=other_dept, category=category, reporter=reporter, tech=tech, other=other, asset=asset)

    def kinds(self, table):
        return [kind for kind, sql in self.statements if f"{self.schema}.{table}" in sql]


@contextmanager
def experiment(step, run_id, create_tables=True):
    lab = Lab(step, run_id)
    check(version('SQLAlchemy') == '2.1.6' and version('psycopg') == '3.3.6', 'Pinned SQLAlchemy and psycopg versions are used.')
    def before_cursor(connection, cursor, statement, parameters, context, executemany):
        kind = statement.lstrip().split(None, 1)[0].upper()
        if kind == 'WITH':
            # A compiled CTE starts with WITH but is still one SELECT/DML
            # round trip. Use SQLAlchemy's statement type, not a SQL parser.
            compiled = getattr(context, 'compiled', None)
            expression = getattr(compiled, 'statement', None)
            for flag, operation in [('is_select','SELECT'),('is_insert','INSERT'),('is_update','UPDATE'),('is_delete','DELETE')]:
                if getattr(expression, flag, False):
                    kind = operation
                    break
        if kind in {'SELECT','INSERT','UPDATE','DELETE'}:
            lab.statements.append((kind, statement))
    event.listen(engine, 'before_cursor_execute', before_cursor)
    physical = None
    try:
        with lab.engine.begin() as c:
            identity = c.execute(text("SELECT current_database(),current_user,pg_backend_pid(),current_setting('server_version_num')::int")).one()
            check(identity[:2] == ('college_learning','college_learner') and 180000 <= identity[3] < 190000
                  and c.scalar(text('SELECT to_regnamespace(:name) IS NULL'), {'name': lab.schema}), 'The learner connects to PostgreSQL 18 with a free study namespace.')
            physical = c.connection.driver_connection
            c.execute(CreateSchema(lab.schema))
            if create_tables:
                Base.metadata.create_all(c)
            c.execute(text(f'CREATE TABLE {lab.schema}.lab_run (run_id uuid PRIMARY KEY, writer_backend_pid integer NOT NULL, expected_snapshot jsonb NOT NULL DEFAULT \'{{}}\')'))
            c.execute(text(f'INSERT INTO {lab.schema}.lab_run (run_id,writer_backend_pid) VALUES (:run,:pid)'), {'run': run_id, 'pid': identity[2]})
        print(f'writer_backend_pid={identity[2]}')
        yield lab
        check(all(not s.in_transaction() and not s.identity_map for s in lab.sessions) and engine.pool.checkedout() == 0,
              'Every scenario Session has closed its transaction and returned its checkout.')
        # Preserve PostgreSQL JSON text directly: Decimal values must not pass
        # through binary float while recording the independent SQL fingerprint.
        with lab.engine.begin() as c:
            tables = c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname=:schema AND tablename <> 'lab_run' ORDER BY tablename"), {'schema':lab.schema}).scalars().all()
            fragments=[]
            for name in tables:
                assert name.replace('_','').isalnum()
                fragments.extend([f"'{name}'", f"(SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),'[]'::jsonb) FROM {lab.schema}.{name} AS t)"])
            snapshot = c.scalar(text('SELECT jsonb_build_object(' + ','.join(fragments) + ')::text'))
            c.execute(text(f'UPDATE {lab.schema}.lab_run SET expected_snapshot=CAST(:snapshot AS jsonb) WHERE run_id=:run'), {'snapshot':snapshot,'run':run_id})
    finally:
        for s in lab.sessions:
            s.close()
        for connection in lab.drivers:
            connection.close()
        event.remove(engine, 'before_cursor_execute', before_cursor)
        engine.dispose()
    check(physical is not None and physical.closed and all(c.closed for c in lab.drivers),
          'The writer and all independent driver connections are disposed.')


def run(step, scenario, **options):
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-id',required=True,type=UUID)
    with experiment(step,parser.parse_args().run_id,**options) as lab:
        scenario(lab)
