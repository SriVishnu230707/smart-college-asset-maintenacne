"""Observe a real deadlock, ordered success, and full-transaction retry scope."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import psycopg
from sqlalchemy import text,update
from sqlalchemy.exc import DBAPIError
from college_maintenance.models import Asset
from college_maintenance.retries import retry_transaction
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed

def scenario(lab):
    ids=seed(lab);first=lab.driver();second=lab.driver();observer=lab.driver()
    update_sql=f'UPDATE {lab.schema}.assets SET location=%s WHERE id=%s'
    barrier=Barrier(2)
    def competing(connection,keys,reverse=False):
        connection.execute('BEGIN')
        try:
            connection.execute(update_sql,('First locked row',keys[0]))
            if reverse:barrier.wait(timeout=4)
            connection.execute(update_sql,('Both rows written',keys[1]));connection.execute('COMMIT')
            return 'committed'
        except psycopg.Error as error:
            connection.execute('ROLLBACK');return error.sqlstate
        finally:
            if connection.info.transaction_status.name!='IDLE':connection.execute('ROLLBACK')
    with ThreadPoolExecutor(max_workers=2) as executor:
        a=executor.submit(competing,first,[ids['asset'],ids['other_asset']],True)
        b=executor.submit(competing,second,[ids['other_asset'],ids['asset']],True)
        outcomes=sorted([a.result(timeout=9),b.result(timeout=9)])
    check(outcomes==['40P01','committed'],'Reversed row acquisition produces one real PostgreSQL deadlock victim and one committed transaction.')
    keys=sorted([ids['asset'],ids['other_asset']])
    with ThreadPoolExecutor(max_workers=2) as executor:
        a=executor.submit(competing,first,keys);b=executor.submit(competing,second,keys)
        check(a.result(timeout=8)==b.result(timeout=8)=='committed','Consistent row ordering permits both competing transactions to commit.')
    sql=f'SELECT location FROM {lab.schema}.assets WHERE id=%s'
    baseline=observer.execute(sql,(ids['asset'],)).fetchone()[0]
    attempts=[]
    def operation(session):
        attempts.append(session)
        session.execute(update(Asset).where(Asset.id==ids['asset']).values(location='Retried operation'))
        if len(attempts)<3:session.execute(text("DO $$ BEGIN RAISE EXCEPTION USING ERRCODE='40001', MESSAGE='synthetic serialization conflict'; END $$"))
        return 'success'
    def paused(delay):
        check(observer.execute(sql,(ids['asset'],)).fetchone()[0]==baseline,'The failed attempt is fully rolled back before retry backoff begins.')
    result=retry_transaction(operation,session_factory=lab.session,pause=paused)
    check(result=='success' and len(attempts)==3 and len({id(s) for s in attempts})==3,'Retry starts a fresh Session and reruns the entire operation, including its writes.')
    check(observer.execute(sql,(ids['asset'],)).fetchone()[0]=='Retried operation','Only the final successful full transaction becomes durable.')
    calls=[]
    def not_retryable(session):calls.append(True);session.execute(text('SELECT 1/0'))
    try:retry_transaction(not_retryable,session_factory=lab.session,pause=lambda delay:None)
    except DBAPIError as error:check(error.orig.sqlstate=='22012' and len(calls)==1,'Nonretryable database errors are propagated without indiscriminate retries.')
    else:raise AssertionError('Division error swallowed')
    calls.clear()
    def exhausted(session):
        calls.append(True);session.execute(text("DO $$ BEGIN RAISE EXCEPTION USING ERRCODE='40001', MESSAGE='persistent serialization conflict'; END $$"))
    try:retry_transaction(exhausted,session_factory=lab.session,attempts=2,pause=lambda delay:None)
    except DBAPIError:check(len(calls)==2,'Retry attempts are bounded and preserve the final database error.')
    else:raise AssertionError('Exhaustion swallowed')
    check(all(not s.in_transaction() for s in attempts),'Every failed and successful retry Session has exited its transaction.')

if __name__=='__main__':run(45,scenario)
