"""Compare snapshots and a two-row write-skew fixture at stronger isolation."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import psycopg
from sqlalchemy import text
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed

def scenario(lab):
    ids=seed(lab);first=lab.driver();second=lab.driver();observer=lab.driver()
    select_sql=f'SELECT location FROM {lab.schema}.assets WHERE id=%s'
    update_sql=f'UPDATE {lab.schema}.assets SET location=%s WHERE id=%s'
    first.execute('BEGIN ISOLATION LEVEL REPEATABLE READ')
    check(first.execute(select_sql,(ids['asset'],)).fetchone()[0]=='Original Lab','REPEATABLE READ establishes its row snapshot at the first read.')
    second.execute(update_sql,('Committed after snapshot',ids['asset']))
    check(first.execute(select_sql,(ids['asset'],)).fetchone()[0]=='Original Lab','A later REPEATABLE READ statement retains the earlier snapshot after an external commit.')
    try:first.execute(update_sql,('Attempt stale update',ids['asset']))
    except psycopg.errors.SerializationFailure:
        first.execute('ROLLBACK');check(True,'Updating a row changed since the REPEATABLE READ snapshot raises SQLSTATE 40001.')
    else:raise AssertionError('Stale RR update accepted')
    check(first.execute(select_sql,(ids['asset'],)).fetchone()[0]=='Committed after snapshot','After rollback a fresh transaction sees the new committed version.')
    count_sql=f"SELECT count(*) FROM {lab.schema}.assets WHERE location='available'"
    keys=[ids['asset'],ids['other_asset']]
    def reset():
        for key in keys:observer.execute(update_sql,('available',key))
    reset()
    for connection in (first,second):
        connection.execute('BEGIN ISOLATION LEVEL REPEATABLE READ')
        if connection.execute(count_sql).fetchone()[0]!=2:raise AssertionError('Bad skew fixture')
    first.execute(update_sql,('unavailable',keys[0]));second.execute(update_sql,('unavailable',keys[1]))
    first.execute('COMMIT');second.execute('COMMIT')
    check(observer.execute(count_sql).fetchone()[0]==0,'Disjoint writes can both commit under REPEATABLE READ and violate a hypothetical at-least-one-available predicate.')
    reset()
    for connection in (first,second):
        connection.execute('BEGIN ISOLATION LEVEL SERIALIZABLE')
        if connection.execute(count_sql).fetchone()[0]!=2:raise AssertionError('Bad serializable fixture')
    states={}
    for index,connection in enumerate((first,second)):
        try:connection.execute(update_sql,('unavailable',keys[index]))
        except psycopg.errors.SerializationFailure:connection.execute('ROLLBACK');states[index]='40001'
    for index,connection in enumerate((first,second)):
        if index in states:continue
        try:connection.execute('COMMIT');states[index]='committed'
        except psycopg.errors.SerializationFailure:connection.execute('ROLLBACK');states[index]='40001'
    check(sorted(states.values())==['40001','committed'],'SERIALIZABLE aborts one conflicting transaction instead of committing the write-skew history.')
    check(observer.execute(count_sql).fetchone()[0]==1,'The remaining committed serializable history preserves the demonstrated predicate.')
    with lab.engine.connect().execution_options(isolation_level='SERIALIZABLE') as connection:
        check(connection.scalar(text('SHOW transaction_isolation'))=='serializable','SQLAlchemy selects the stronger level before its transaction begins.')
        connection.rollback()
    with lab.engine.connect() as connection:
        check(connection.scalar(text('SHOW transaction_isolation'))=='read committed','Returning a checkout resets its temporary isolation setting.')
    check(first.info.transaction_status.name==second.info.transaction_status.name=='IDLE','All successful and aborted strong-isolation transactions are ended explicitly.')

if __name__=='__main__':run(46,scenario)
