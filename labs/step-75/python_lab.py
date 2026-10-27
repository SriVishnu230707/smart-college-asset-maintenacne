from pathlib import Path
from importlib.metadata import version
import asyncio,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import select,text,update
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
from sqlalchemy.orm import raiseload
from sqlalchemy.exc import InvalidRequestError
from college_maintenance.database import engine
from college_maintenance.models import MaintenanceTicket,Asset
from college_maintenance.workflow import report_ticket
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed

def scenario(lab):
    ids=seed(lab);check(version('greenlet')=='3.2.4','The explicit async bridge dependency is pinned and installed.')
    async def exercise():
        target=create_async_engine(engine.url,pool_size=2,max_overflow=0,pool_timeout=3,hide_parameters=True).execution_options(schema_translate_map={None:lab.schema})
        factory=async_sessionmaker(bind=target.execution_options(schema_translate_map={None:lab.schema}),expire_on_commit=False)
        pids=[]
        try:
            async with factory() as s,s.begin():
                ticket=await s.run_sync(lambda sync:report_ticket(sync,ids['reporter'],asset_id=ids['asset'],title='Async report',description='Supported SQLAlchemy bridge'))
                await s.execute(update(Asset).where(Asset.id==ids['asset']).values(location='Async native update'))
                ticket_id=ticket.id
            try:
                async with factory() as s,s.begin():
                    await s.run_sync(lambda sync:report_ticket(sync,ids['reporter'],asset_id=ids['asset'],title='Async rollback',description='Injected failure'))
                    await s.flush();raise RuntimeError('injected async failure')
            except RuntimeError:check(True,'Async transaction context propagates failure and rolls back the whole use case.')
            events=[asyncio.Event(),asyncio.Event()]
            async def worker(number):
                async with factory() as s,s.begin():
                    pid=await s.scalar(text('SELECT pg_backend_pid()'));events[number].set()
                    await events[1-number].wait();return pid
            pids=await asyncio.wait_for(asyncio.gather(worker(0),worker(1)),timeout=8)
            check(len(set(pids))==2,'Concurrent tasks own distinct AsyncSessions and physical connections.')
            async with factory() as s:
                ticket=await s.scalar(select(MaintenanceTicket).where(MaintenanceTicket.id==ticket_id).options(raiseload('*')))
                try:_=ticket.comments
                except InvalidRequestError:check(True,'Explicit loading policy rejects accidental relationship I/O outside an awaited query.')
                else:raise AssertionError('Unexpected implicit relationship load')
            async with target.connect() as c:
                sizes=[]
                statement=select(MaintenanceTicket.id).where(MaintenanceTicket.title=='Stream fixture').execution_options(yield_per=500)
                async with c.stream(statement) as result:
                    async for batch in result.partitions(500):sizes.append(len(batch))
                check(sum(sizes)==5000 and max(sizes)<=500,'Server-side async streaming processes 5000 IDs in bounded partitions without materializing ORM collections.')
            check(target.sync_engine.pool.checkedout()==0,'All asynchronous Sessions and streams release their connection checkouts.')
        finally:await target.dispose()
        return pids
    with lab.engine.begin() as c:
        c.exec_driver_sql(f"INSERT INTO {lab.schema}.maintenance_tickets(asset_id,department_id,reported_by_id,title,description,priority) SELECT %s,%s,%s,'Stream fixture','Synthetic export','low' FROM generate_series(1,5000)",(ids['asset'],ids['dept'],ids['reporter']))
    if sys.platform=='win32':
        # psycopg async requires a selector loop, not Windows' Proactor default.
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:pids=runner.run(exercise())
    else:pids=asyncio.run(exercise())
    observer=lab.driver()
    check(observer.execute(f"SELECT title FROM {lab.schema}.maintenance_tickets WHERE title LIKE 'Async %%' ORDER BY title").fetchall()==[('Async report',)],'Independent SQL confirms async commit and injected rollback visibility.')
    check(observer.execute('SELECT count(*) FROM pg_stat_activity WHERE pid=ANY(%s)',(pids,)).fetchone()[0]==0,'Async disposal closes both concurrent physical backends.')
    with lab.engine.begin() as c:c.exec_driver_sql(f"DELETE FROM {lab.schema}.maintenance_tickets WHERE title='Stream fixture'")
    print('run_sync reuses proven synchronous database logic via SQLAlchemy greenlets; it does not make arbitrary blocking I/O asynchronous. The production API remains synchronous. Collection joined loading/unique processing require a different export strategy from ID streaming.')

if __name__=='__main__':run(75,scenario)
