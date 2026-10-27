from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed
from labs.shared.performance_lab import workload,explain,nodes,save_plans,QUEUE

def scenario(lab):
    seed(lab)
    with workload(lab,80000) as c:
        expected=c.exec_driver_sql(QUEUE).all();before=explain(c,QUEUE)
        c.exec_driver_sql('CREATE INDEX bench_feed_full ON bench_tickets(department,status,created_at DESC,id DESC)')
        full=explain(c,QUEUE)
        c.exec_driver_sql('DROP INDEX bench_feed_full')
        c.exec_driver_sql("CREATE INDEX bench_feed_active ON bench_tickets(department,created_at DESC,id DESC) INCLUDE(title) WHERE status='open'")
        partial=explain(c,QUEUE)
        check(c.exec_driver_sql(QUEUE).all()==expected,'Index alternatives preserve the exact ordered ticket page.')
        check(any(n.get('Index Name')=='bench_feed_active' for n in nodes(partial['Plan'])),'The measured sparse active-queue predicate uses its partial covering index.')
        check(not any('Sort' in n['Node Type'] for n in nodes(partial['Plan'])),'Index order satisfies the bounded queue ordering without a separate sort.')
        check(any('Index' in n['Node Type'] for n in nodes(full['Plan'])),'The full composite alternative is also measured rather than assumed.')
        size=c.exec_driver_sql("SELECT pg_relation_size('bench_feed_active'),pg_relation_size('bench_tickets')").one()
        check(0<size[0]<size[1],'The sparse index has a measured storage footprint smaller than the heap.')
        check(c.exec_driver_sql("SELECT count(*) FROM pg_indexes WHERE tablename='bench_tickets' AND indexdef LIKE 'CREATE UNIQUE INDEX%%'").scalar_one()==1,'The primary key already supplies its unique index; another ID index would be redundant.')
        closed=explain(c,"SELECT count(*) FROM bench_tickets WHERE status='closed'")
        check(not any(n.get('Index Name')=='bench_feed_active' for n in nodes(closed['Plan'])),'A partial open-only index cannot answer a closed-row predicate.')
        c.exec_driver_sql('CREATE INDEX bench_title_lower ON bench_tickets(lower(title))')
        check('lower(title)' in c.exec_driver_sql("SELECT pg_get_indexdef('bench_title_lower'::regclass)").scalar_one(),'Expression indexing is explicit; it is rejected for this feed because title is not a filter.')
        save_plans(55,query=QUEUE,rows=80000,baseline=before,composite=full,partial_covering=partial,closed_scan=closed,index_bytes=size[0])
        print('Decision: sparse feed partial index is useful for this workload; reject duplicate ID and unqueried title indexes. Production migration requires production-shaped evidence.')
    check(lab.driver().execute('SELECT 1').fetchone()==(1,),'Independent PostgreSQL remains usable after temporary index disposal.')

if __name__=='__main__':run(55,scenario)
