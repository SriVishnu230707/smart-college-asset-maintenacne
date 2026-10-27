from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed
from labs.shared.performance_lab import workload,explain,nodes,save_plans,QUEUE

def scenario(lab):
    seed(lab)
    with workload(lab,100000) as c:
        c.exec_driver_sql('UPDATE bench_tickets SET department=1 WHERE id%%10<>0',())
        c.exec_driver_sql('ALTER TABLE bench_tickets ALTER COLUMN department SET STATISTICS 200')
        c.exec_driver_sql('ANALYZE bench_tickets')
        c.exec_driver_sql('CREATE INDEX bench_department ON bench_tickets(department)')
        common=explain(c,'SELECT * FROM bench_tickets WHERE department=1')
        rare=explain(c,'SELECT * FROM bench_tickets WHERE department=0')
        check(common['Plan']['Actual Rows']==90000 and rare['Plan']['Actual Rows']==5000,'The skewed workload has known 90-percent and 5-percent department selectivities.')
        check(any(n['Node Type']=='Seq Scan' for n in nodes(common['Plan'])),'Scanning the heap is justified for the measured very common full-row predicate.')
        check(any('Index' in n['Node Type'] for n in nodes(rare['Plan'])),'The same index benefits a selective predicate on the same table.')
        stats=c.exec_driver_sql("SELECT n_distinct,most_common_vals::text,most_common_freqs FROM pg_stats WHERE tablename='bench_tickets' AND attname='department' AND schemaname=(SELECT nspname FROM pg_namespace WHERE oid=pg_my_temp_schema())").one()
        check(stats[0]==3 and '1' in stats[1] and max(stats[2])>0.8,'ANALYZE records skew in most-common-value statistics, rather than assuming uniform data.')
        check(abs(common['Plan']['Plan Rows']-90000)<10000,'Estimated cardinality is checked against an explicit broad tolerance, not an elapsed-time promise.')
        plans=[explain(c,'SELECT id FROM bench_tickets WHERE department=0 LIMIT 20') for _ in range(3)]
        check(all(p['Plan']['Actual Rows']==20 for p in plans),'Repeated samples preserve the same query cardinality while timings may vary.')
        save_plans(56,configuration={'rows':100000,'department_one_fraction':0.9,'statistics_target':200},common=common,rare=rare,repeated=plans)
        print('Observed milliseconds:',[p['Execution Time'] for p in plans]);print('Decision: do not enforce hardware-specific speed thresholds or infer production selectivity from tiny fixtures.')
    check(lab.driver().execute('SELECT current_user').fetchone()[0]=='college_learner','An independent observer confirms workload disposal did not change runtime identity.')

if __name__=='__main__':run(56,scenario)
