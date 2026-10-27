from pathlib import Path
from uuid import uuid4
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import select,func
from college_maintenance.models import Asset
from college_maintenance.imports import import_assets
from college_maintenance.reads import scope_for_actor
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed

def scenario(lab):
    ids=seed(lab)
    row=dict(asset_code='IMPORT-1',name='Imported',department_id=ids['dept'],category_id=ids['category'])
    with lab.session() as s,s.begin():
        result=import_assets(s,scope_for_actor(s,ids['super']),[row,row,{**row,'asset_code':'BAD','department_id':uuid4()},{**row,'asset_code':'EMPTY','name':' '}],policy='reject_rows')
        check(result=={'inserted':1,'duplicates':1,'rejected':[{'row':3,'reason':'integrity'},{'row':4,'reason':'invalid_input'}]},'Per-row savepoints distinguish duplicates, invalid references and invalid values without exposing SQL details.')
    try:
        with lab.session() as s,s.begin():import_assets(s,scope_for_actor(s,ids['super']),[{**row,'asset_code':'ATOMIC-1'},{**row,'name':''}])
    except ValueError:check(True,'Atomic import propagates invalid input to roll back the outer operation.')
    with lab.session() as s:
        check(s.scalar(select(func.count()).select_from(Asset).where(Asset.asset_code=='ATOMIC-1'))==0,'A new Session confirms the first atomic row did not survive.')
        try:import_assets(s,scope_for_actor(s,ids['admin']),[])
        except PermissionError:check(True,'Department administration does not imply college-wide import authority.')
        else:raise AssertionError('Import scope bypass')
    with lab.engine.begin() as c:
        c.exec_driver_sql('CREATE TEMP TABLE imported_assets(code text,name text) ON COMMIT DROP')
        with c.connection.driver_connection.cursor() as cursor:
            with cursor.copy('COPY imported_assets(code,name) FROM STDIN') as copy:
                copy.write_row(('COPY-1','Copied asset'));copy.write_row(('COPY-2','Second copy'))
        count=c.exec_driver_sql(f"INSERT INTO {lab.schema}.assets(asset_code,name,department_id,category_id) SELECT code,name,%s,%s FROM imported_assets ON CONFLICT(asset_code) DO NOTHING RETURNING id",(ids['dept'],ids['category'])).all()
        check(len(count)==2,'COPY stages typed rows inside the caller transaction before set-based insertion with a named conflict target.')
    check(lab.driver().execute(f"SELECT count(*) FROM {lab.schema}.assets WHERE asset_code LIKE 'COPY-%%' OR asset_code='IMPORT-1'").fetchone()[0]==3,'Independent SQL confirms only the three intended imported assets committed.')
    print('Import contract: clean pending state before reject_rows; bounded input supplied by caller; duplicate identity is skipped, not overwritten. COPY staging is an alternative, not an implicit partial-commit policy.')

if __name__=='__main__':run(57,scenario)
