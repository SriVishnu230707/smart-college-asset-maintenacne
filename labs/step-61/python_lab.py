from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import create_engine,text
from sqlalchemy.exc import TimeoutError
from sqlalchemy.orm import sessionmaker
from college_maintenance.database import engine,pool_settings
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed,headers
from fastapi.testclient import TestClient
from college_maintenance.api import create_app

def scenario(lab):
    ids=seed(lab);pool=create_engine(engine.url,pool_size=1,max_overflow=1,pool_timeout=.2,pool_pre_ping=True,hide_parameters=True)
    try:
        one=pool.connect();two=pool.connect()
        try:
            check(pool.pool.checkedout()==2,'One persistent plus one overflow slot establishes an explicit two-connection process budget.')
            try:pool.connect()
            except TimeoutError:check(True,'A third checkout fails with a bounded pool timeout instead of waiting indefinitely.')
            else:raise AssertionError('Pool bound ignored')
        finally:one.close();two.close()
        check(pool.pool.checkedout()==0,'Closing success paths returns every checkout.')
        factory=sessionmaker(bind=pool.execution_options(schema_translate_map={None:lab.schema}))
        with TestClient(create_app(session_factory=factory,authenticate=lambda token:ids.get(token))) as api:
            check(api.get('/reports/costs',headers=headers('admin')).status_code==200,'The real API succeeds through the bounded pool.')
            check(api.get('/reports/costs',headers=headers('reporter')).status_code==403,'The real API error path retains its resource-scoped denial.')
        check(pool.pool.checkedout()==0,'Both API response and error cleanup leave zero checked-out connections.')
        with pool.connect() as c:old=c.scalar(text('SELECT pg_backend_pid()'))
        check(lab.driver().execute('SELECT pg_terminate_backend(%s)',(old,)).fetchone()[0],'A deliberately disconnected idle backend simulates a stale pooled connection.')
        with pool.connect() as c:check(c.scalar(text('SELECT pg_backend_pid()'))!=old,'Pre-ping replaces the dead connection at checkout without replaying a transaction.')
        check(pool_settings()=={'pool_size':1,'max_overflow':0,'pool_timeout':5},'Defaults preserve the original learning configuration; deployment can choose bounded settings explicitly.')
        print('Budget: workers * (pool_size + max_overflow), plus migrations, observers and operational headroom. Pre-ping does not make a mid-transaction disconnect transparently retryable.')
    finally:pool.dispose()
    check(lab.driver().execute('SELECT count(*) FROM pg_stat_activity WHERE pid=%s',(old,)).fetchone()[0]==0,'Independent SQL confirms the terminated backend is gone.')

if __name__=='__main__':run(61,scenario)
