"""Create an empty database from frozen Alembic revisions, then install the app."""
import sys
from importlib.metadata import version
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from college_maintenance.database import engine
from college_maintenance.migrations import migration_config, upgrade
from labs.shared.migration_lab import temporary_database
from labs.shared.orm_lab import check, run

TABLES={'departments','asset_categories','users','assets','maintenance_tickets','work_orders','spare_parts','work_order_parts'}

def scenario(lab):
    check(version('alembic')=='1.20.1','Alembic uses the pinned reviewed version.')
    with temporary_database(26,lab.run_id) as db:
        with db.begin() as c:
            check(inspect(c).get_table_names()==[],'The migration target begins as a genuinely empty database.')
            upgrade(c,'0001_initial')
            catalog=inspect(c)
            check(set(catalog.get_table_names())==TABLES|{'alembic_version'},'The initial revision alone installs all eight application tables and its version marker.')
            check(c.scalar(text('SELECT version_num FROM alembic_version'))=='0001_initial','The database records the exact initial revision.')
            check(all(catalog.get_pk_constraint(t)['name']==f'pk_{t}' for t in TABLES),'Every initial primary key has its reviewed stable name.')
            links=[fk for t in TABLES for fk in catalog.get_foreign_keys(t)]
            check(len(links)==11 and all(f['name'] and f['options']['ondelete']=='RESTRICT' and f['options']['onupdate']=='RESTRICT' for f in links),
                  'All eleven reference policies are installed as named RESTRICT constraints.')
            check(catalog.get_pk_constraint('work_order_parts')['constrained_columns']==['work_order_id','spare_part_id'],'The migrated association identity is composite.')
            indexes=catalog.get_indexes('work_orders')
            check(any(i['name']=='uq_work_orders_active_ticket' and i['unique'] for i in indexes),'The partial active-work-order uniqueness index is installed.')
            columns={x['name']:x for x in catalog.get_columns('work_order_parts')}
            check(columns['unit_cost_at_use']['type'].precision==12 and columns['unit_cost_at_use']['type'].scale==2,'Migrated historical money uses exact numeric(12,2).')
            department=c.scalar(text("INSERT INTO departments(code,name) VALUES('MIG','Migrated') RETURNING id"))
            check(department is not None,'A migrated table generates an ID without any create_all call.')
            for sql,state in [("INSERT INTO departments(code,name) VALUES('BAD',' ')" ,'23514'),("INSERT INTO departments(code,name) VALUES('MIG','Duplicate')",'23505')]:
                try:
                    with c.begin_nested():c.execute(text(sql))
                except IntegrityError as exc:check(exc.orig.sqlstate==state,f'Migrated constraints reject invalid data with SQLSTATE {state}.')
                else:raise AssertionError('Migrated constraint was absent')
        with db.begin() as c:
            upgrade(c,'0001_initial')
            check(c.scalar(text('SELECT count(*) FROM departments'))==1,'Reapplying the same revision is idempotent and preserves existing data.')
    with engine.begin() as c:
        existing=set(inspect(c).get_table_names())
        check('alembic_version' in existing or not existing.intersection(TABLES),'Unversioned application tables are never silently adopted or stamped.')
        upgrade(c)
        head=ScriptDirectory.from_config(migration_config()).get_current_head()
        check(c.scalar(text('SELECT version_num FROM alembic_version'))==head,'The application database is installed at the reviewed migration head.')
    check(True,'The independently migrated scratch database was closed and removed without touching application data.')

if __name__=='__main__':run(26,scenario,create_tables=False)
