from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed
from labs.shared.performance_lab import workload,explain,nodes,save_plans,QUEUE

def scenario(lab):
    seed(lab)
    with workload(lab) as c:
        plan=explain(c,QUEUE);tree=list(nodes(plan['Plan']))
        rows=c.exec_driver_sql(QUEUE).all()
        check(len(rows)==20,'The representative department queue returns its bounded expected page.')
        check(plan['Plan']['Actual Rows']==len(rows),'EXPLAIN ANALYZE executes the SELECT and reports actual output cardinality.')
        check(any(n['Node Type']=='Seq Scan' for n in tree),'The no-feed-index baseline scans the synthetic relation.')
        check(any('Sort' in n['Node Type'] for n in tree),'The baseline pays for deterministic ordering separately.')
        check(all(n['Actual Loops']>=1 and n['Plan Rows']>=0 for n in tree),'Each visited plan node exposes estimates, actual rows and loops.')
        check('Shared Hit Blocks' in plan['Plan'] or 'Local Hit Blocks' in plan['Plan'],'Buffer observations distinguish server I/O/cache work from elapsed time.')
        save_plans(54,configuration={'rows':40000,'departments':20,'open_fraction':'1/101','query':QUEUE},baseline=plan)
        print('Plan nodes:',[n['Node Type'] for n in tree]);print('Execution milliseconds (observation only):',plan['Execution Time'])
    check(lab.driver().execute("SELECT count(*) FROM pg_class WHERE relname='bench_tickets' AND relnamespace=pg_my_temp_schema()").fetchone()[0]==0,'Workload is connection-local and absent from the independent observer.')

if __name__=='__main__':run(54,scenario)
