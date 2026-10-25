"""Review rename detection and evolve actual populated migration-owned data."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from college_maintenance.database import engine
from college_maintenance.models import Base
from college_maintenance.migrations import migration_config, upgrade
from labs.shared.migration_lab import temporary_database
from labs.shared.orm_lab import check, run

def scenario(lab):
    with temporary_database(27,lab.run_id) as db:
        with db.begin() as c:
            upgrade(c,'0001_initial')
            dept=c.scalar(text("INSERT INTO departments(code,name) VALUES('MIG','Migration') RETURNING id"))
            cat=c.scalar(text("INSERT INTO asset_categories(code,name) VALUES('PC','Computer') RETURNING id"))
            active=c.scalar(text("INSERT INTO assets(asset_code,name,department_id,category_id) VALUES('OLD-A','Existing active',:d,:c) RETURNING id"),{'d':dept,'c':cat})
            retired=c.scalar(text("INSERT INTO assets(asset_code,name,status,department_id,category_id) VALUES('OLD-R','Existing retired','retired',:d,:c) RETURNING id"),{'d':dept,'c':cat})
            part=c.scalar(text("INSERT INTO spare_parts(sku,name,current_unit_cost) VALUES('OLD-PART','Preserved catalog label',12.50) RETURNING id"))
            changes=compare_metadata(MigrationContext.configure(c),Base.metadata)
            rename_candidates={(d[0],d[3].name) for d in changes if isinstance(d,tuple) and d[0] in ('add_column','remove_column') and d[2]=='spare_parts'}
            check(('add_column','display_name') in rename_candidates and ('remove_column','name') in rename_candidates,
                  'Autogenerate suggests add/drop for a rename; manual review identifies the data-loss hazard.')
            check(c.scalar(text('SELECT count(*) FROM assets'))==2,'The pre-migration database contains real populated active and retired rows.')
        with db.begin() as c:
            upgrade(c,'0002_condition')
            check(c.execute(text('SELECT condition_note FROM assets WHERE id IN (:a,:r) ORDER BY asset_code'),{'a':active,'r':retired}).scalars().all()==['Not assessed','Retired inventory'],
                  'The nullable-add/backfill/NOT NULL sequence populates both existing asset states deliberately.')
            columns={x['name']:x for x in inspect(c).get_columns('assets')}
            check(not columns['condition_note']['nullable'] and 'Not assessed' in columns['condition_note']['default'],
                  'The final required note has a default for old callers and an installed NOT NULL rule.')
            check(c.scalar(text('SELECT display_name FROM spare_parts WHERE id=:id'),{'id':part})=='Preserved catalog label',
                  'A true column rename preserves the catalog label and original part identity.')
            check(c.scalar(text('SELECT name FROM assets WHERE id=:id'),{'id':active})=='Existing active','Unrelated populated asset values and identities are preserved.')
            for value,state in [(None,'23502'),(' ','23514')]:
                try:
                    with c.begin_nested():c.execute(text('UPDATE assets SET condition_note=:note WHERE id=:id'),{'note':value,'id':active})
                except IntegrityError as exc:check(exc.orig.sqlstate==state,f'The evolved database rejects invalid required notes with SQLSTATE {state}.')
                else:raise AssertionError('An invalid required note was accepted')
            c.execute(text("UPDATE assets SET condition_note='New information' WHERE id=:id"),{'id':active})
        with db.begin() as c:
            command.downgrade(migration_config(c),'0001_initial')
            check('condition_note' not in {x['name'] for x in inspect(c).get_columns('assets')},'The isolated downgrade demonstrates its explicit loss of newly recorded condition information.')
            check(c.scalar(text('SELECT name FROM spare_parts WHERE id=:id'),{'id':part})=='Preserved catalog label','The reversible rename restores the old column without losing the part label.')
            check(c.scalar(text('SELECT count(*) FROM assets'))==2,'The downgrade preserves original rows while discarding only the documented new attribute.')
            upgrade(c,'0002_condition')
            check(c.scalar(text('SELECT condition_note FROM assets WHERE id=:id'),{'id':active})=='Not assessed','Re-upgrade backfills deterministically; discarded information is not magically recoverable.')
    with engine.begin() as c:
        upgrade(c)
        check('condition_note' in {x['name'] for x in inspect(c).get_columns('assets')},'The application database receives the reviewed forward migration only.')

if __name__=='__main__':run(27,scenario,create_tables=False)
