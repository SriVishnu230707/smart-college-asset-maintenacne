from pathlib import Path
import sys,threading,time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed

def scenario(lab):
    ids=seed(lab);owner=lab.driver();waiter=lab.driver();monitor=lab.driver();errors=[];started=threading.Event()
    owner.execute('BEGIN');owner.execute(f'SELECT id FROM {lab.schema}.assets WHERE id=%s FOR UPDATE',(ids['asset'],))
    def blocked_update():
        try:
            started.set();waiter.execute(f'UPDATE {lab.schema}.assets SET location=%s WHERE id=%s',('After observed wait',ids['asset']))
        except BaseException as exc:errors.append(exc)
    thread=threading.Thread(target=blocked_update);thread.start()
    try:
        assert started.wait(2)
        deadline=time.monotonic()+4;blockers=[]
        while time.monotonic()<deadline:
            blockers=monitor.execute('SELECT pg_blocking_pids(%s)',(waiter.info.backend_pid,)).fetchone()[0]
            if owner.info.backend_pid in blockers:break
            time.sleep(.02)
        check(owner.info.backend_pid in blockers,'pg_blocking_pids identifies the actual independent backend holding the asset lock.')
        row=monitor.execute('SELECT state,wait_event_type FROM pg_stat_activity WHERE pid=%s',(waiter.info.backend_pid,)).fetchone()
        check(row==('active','Lock'),'pg_stat_activity distinguishes an active blocked query from an idle transaction.')
        check(monitor.execute('SELECT count(*) FROM pg_locks WHERE pid=%s AND NOT granted',(waiter.info.backend_pid,)).fetchone()[0]>=1,'pg_locks exposes the waiter ungranted lock.')
    finally:
        owner.execute('ROLLBACK');thread.join(6)
    check(not thread.is_alive() and not errors,'Releasing the blocker lets the waiting update commit without a timing-based race assertion.')
    owner.execute('BEGIN');owner.execute('SELECT 1')
    check(monitor.execute('SELECT state FROM pg_stat_activity WHERE pid=%s',(owner.info.backend_pid,)).fetchone()[0]=='idle in transaction','A transaction left open is observably different from a released connection.')
    owner.execute('ROLLBACK')
    monitor.execute(f'VACUUM (ANALYZE) {lab.schema}.assets')
    stats=monitor.execute('SELECT last_analyze IS NOT NULL,pg_total_relation_size(relid)>0 FROM pg_stat_all_tables WHERE schemaname=%s AND relname=%s',(lab.schema,'assets')).fetchone()
    check(stats==(True,True),'Autocommit VACUUM ANALYZE maintains the relation and records planner-statistics maintenance.')
    check(monitor.execute('SELECT xact_commit>=0,blks_hit>=0 FROM pg_stat_database WHERE datname=current_database()').fetchone()==(True,True),'Database workload counters are available without claiming an uninstalled pg_stat_statements extension.')
    print('VACUUM reclaims reusable tuple space; ANALYZE samples planner statistics. pg_stat_statements additionally requires server preload/configuration. Never VACUUM inside an ordinary transaction block.')

if __name__=='__main__':run(60,scenario)
