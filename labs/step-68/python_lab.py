from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import MetaData,Table,select
from sqlalchemy.exc import DBAPIError
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed

def scenario(lab):
    seed(lab);schema=lab.schema
    try:
        with lab.engine.begin() as c:
            c.exec_driver_sql(f"CREATE TYPE {schema}.service_state AS ENUM ('planned','done')")
            c.exec_driver_sql(f"CREATE DOMAIN {schema}.service_cost AS numeric(12,2) CHECK(VALUE>=0 AND VALUE<>'NaN'::numeric)")
            c.exec_driver_sql(f'''CREATE TABLE {schema}.service_windows(
                id int PRIMARY KEY,room int NOT NULL CHECK(room BETWEEN 1 AND 100000),
                slot tstzrange NOT NULL CHECK(NOT isempty(slot) AND lower(slot) IS NOT NULL AND upper(slot) IS NOT NULL),
                state {schema}.service_state NOT NULL DEFAULT 'planned',tags text[] NOT NULL,
                cost {schema}.service_cost NOT NULL,
                duration_seconds numeric GENERATED ALWAYS AS(extract(epoch FROM (upper(slot)-lower(slot)))) STORED,
                EXCLUDE USING gist (int4range(room,room,'[]') WITH &&,slot WITH &&))''')
            c.exec_driver_sql(f"INSERT INTO {schema}.service_windows(id,room,slot,tags,cost) VALUES(1,1,'[2026-01-01 10:00+00,2026-01-01 11:00+00)',ARRAY['electrical'],5.25)")
            for identifier,room,slot,amount,state in [(2,1,'[2026-01-01 10:30+00,2026-01-01 11:30+00)',5,'planned'),(3,2,'[2026-01-01 10:00+00,2026-01-01 11:00+00)',-1,'planned'),(4,2,'[2026-01-01 10:00+00,2026-01-01 11:00+00)',1,'unknown')]:
                try:
                    with c.begin_nested():c.exec_driver_sql(f'INSERT INTO {schema}.service_windows(id,room,slot,tags,cost,state) VALUES(%s,%s,%s,ARRAY[]::text[],%s,%s)',(identifier,room,slot,amount,state))
                except DBAPIError as exc:check(exc.orig.sqlstate in {'23P01','23514','22P02'},'Range exclusion, domain validity and enum membership are enforced by PostgreSQL.')
                else:raise AssertionError('Invalid typed schedule accepted')
            c.exec_driver_sql(f"INSERT INTO {schema}.service_windows(id,room,slot,tags,cost) VALUES(5,2,'[2026-01-01 10:00+00,2026-01-01 11:00+00)',ARRAY['mechanical'],0),(6,1,'[2026-01-01 11:00+00,2026-01-01 12:00+00)',ARRAY[]::text[],0)")
            check(c.exec_driver_sql(f'SELECT duration_seconds FROM {schema}.service_windows WHERE id=1').scalar_one()==3600,'Generated duration is calculated from stored range bounds rather than supplied independently.')
            table=Table('service_windows',MetaData(),schema=schema,autoload_with=c)
            check(c.execute(select(table.c.id).where(table.c.tags.contains(['electrical']))).scalars().all()==[1],'Reflected PostgreSQL ARRAY exposes typed containment through SQLAlchemy.')
            multi=c.exec_driver_sql("SELECT '{[1,3),[3,5)}'::int4multirange").scalar_one()
            check(len(multi)==1 and multi[0].lower==1 and multi[0].upper==5,'Multiranges canonicalize adjacent integer ranges.')
            c.exec_driver_sql(f"ALTER TYPE {schema}.service_state ADD VALUE 'cancelled'")
            try:
                with c.begin_nested():c.exec_driver_sql(f"SELECT 'cancelled'::{schema}.service_state")
            except DBAPIError as exc:check(exc.orig.sqlstate=='55P04','A newly added enum label cannot be used until its migration transaction commits.')
            else:raise AssertionError('Unsafe enum use unexpectedly accepted')
        with lab.engine.connect() as c:check(c.exec_driver_sql(f"SELECT 'cancelled'::{schema}.service_state").scalar_one()=='cancelled','The committed enum label is available in a subsequent transaction.')
        first=lab.driver();second=lab.driver();first.execute('BEGIN')
        try:
            first.execute(f"INSERT INTO {schema}.service_windows(id,room,slot,tags,cost) VALUES(7,3,'[2026-01-01 10:00+00,2026-01-01 11:00+00)',ARRAY[]::text[],0)")
            second.execute("SET lock_timeout='150ms'")
            import psycopg
            try:second.execute(f"INSERT INTO {schema}.service_windows(id,room,slot,tags,cost) VALUES(8,3,'[2026-01-01 10:00+00,2026-01-01 11:00+00)',ARRAY[]::text[],0)")
            except psycopg.errors.LockNotAvailable:check(True,'Concurrent overlapping reservations wait on the exclusion constraint rather than both succeeding.')
            else:raise AssertionError('Concurrent overlap accepted')
        finally:first.execute('ROLLBACK')
        check(lab.driver().execute(f'SELECT count(*) FROM {schema}.service_windows').fetchone()[0]==3,'Independent SQL confirms adjacent/different-room schedules and rejects invalid or rolled-back rows.')
    finally:
        with lab.engine.begin() as c:
            c.exec_driver_sql(f'DROP TABLE IF EXISTS {schema}.service_windows')
            c.exec_driver_sql(f'DROP TYPE IF EXISTS {schema}.service_state')
            c.exec_driver_sql(f'DROP DOMAIN IF EXISTS {schema}.service_cost')

if __name__=='__main__':run(68,scenario)
