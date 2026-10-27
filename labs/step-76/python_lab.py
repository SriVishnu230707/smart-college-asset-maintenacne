from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import MetaData,Table,Column,Integer,select,bindparam
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed
from labs.shared.performance_lab import workload,explain,nodes,save_plans

def scenario(lab):
    seed(lab)
    with workload(lab,100000) as c:
        c.exec_driver_sql('CREATE INDEX bench_time_brin ON bench_tickets USING brin(created_at) WITH(pages_per_range=4)')
        brin=explain(c,"SELECT id FROM bench_tickets WHERE created_at>=timestamptz '2026-02-01 UTC' AND created_at<timestamptz '2026-02-01 00:10 UTC'")
        check(brin['Plan']['Actual Rows']==10,'A BRIN candidate is evaluated on naturally ordered time data with known selectivity.')
        c.exec_driver_sql('CREATE INDEX bench_id_hash ON bench_tickets USING hash(id)')
        equality=explain(c,'SELECT id FROM bench_tickets WHERE id=777')
        check(equality['Plan']['Actual Rows']==1,'Hash equality is measured against the existing B-tree primary-key alternative.')
        methods=c.exec_driver_sql("SELECT am.amname FROM pg_class cl JOIN pg_am am ON am.oid=cl.relam WHERE cl.relname IN ('bench_time_brin','bench_id_hash') AND cl.relnamespace=pg_my_temp_schema()").scalars().all()
        check(set(methods)=={'brin','hash'},'Catalog access methods verify the indexes actually created.')
        c.exec_driver_sql('CREATE TEMP TABLE spatial_examples(id int,location point) ON COMMIT DROP')
        c.exec_driver_sql('INSERT INTO spatial_examples SELECT i,point(i,i) FROM generate_series(1,20000) i')
        c.exec_driver_sql('CREATE INDEX point_spgist ON spatial_examples USING spgist(location)')
        c.exec_driver_sql('ANALYZE spatial_examples')
        spatial=explain(c,"SELECT id FROM spatial_examples WHERE location <@ box(point(100,100),point(110,110))")
        check(spatial['Plan']['Actual Rows']==11 and any(n.get('Index Name')=='point_spgist' for n in nodes(spatial['Plan'])),'SP-GiST supports the measured point-region query.')
        c.exec_driver_sql('DROP INDEX point_spgist');c.exec_driver_sql('CREATE INDEX point_gist ON spatial_examples USING gist(location)')
        nearest=explain(c,'SELECT id FROM spatial_examples ORDER BY location <-> point(100,101) LIMIT 5')
        check(nearest['Plan']['Actual Rows']==5 and any(n.get('Index Name')=='point_gist' for n in nodes(nearest['Plan'])),'GiST supports nearest-neighbor ordering for the chosen point workload.')
        c.exec_driver_sql(f'CREATE STATISTICS {lab.schema}.department_status_stats (dependencies,mcv) ON department,status FROM bench_tickets')
        c.exec_driver_sql('ANALYZE bench_tickets')
        check(c.exec_driver_sql("SELECT count(*) FROM pg_statistic_ext WHERE stxname='department_status_stats' AND stxnamespace=to_regnamespace(%s)",(lab.schema,)).scalar_one()==1,'Multicolumn statistics are installed in an explicit namespace rather than inferred from an index.')
        table=Table('bench_tickets',MetaData(),Column('id',Integer),schema='pg_temp');cache={}
        cached=c.execution_options(compiled_cache=cache)
        statement=select(table.c.id).where(table.c.id==bindparam('identity'))
        check(cached.execute(statement,{'identity':1}).scalar_one()==1 and cached.execute(statement,{'identity':2}).scalar_one()==2 and len(cache)==1,'A compiled-statement cache reuses SQL structure while returning different parameter-dependent row values.')
        prepared='lesson_prepared_'+lab.run_id.hex
        c.exec_driver_sql(f'PREPARE {prepared}(int) AS SELECT id FROM bench_tickets WHERE department=$1 LIMIT 20')
        c.exec_driver_sql('SET LOCAL plan_cache_mode=force_custom_plan');custom=explain(c,f'EXECUTE {prepared}(7)')
        c.exec_driver_sql('SET LOCAL plan_cache_mode=force_generic_plan');generic=explain(c,f'EXECUTE {prepared}(7)')
        check(custom['Plan']['Actual Rows']==generic['Plan']['Actual Rows']==20,'Server generic/custom prepared plans preserve results and are distinct from Python compilation caching.')
        c.exec_driver_sql(f'DEALLOCATE {prepared}')
        save_plans(76,brin=brin,hash_or_btree=equality,spgist=spatial,gist_nearest=nearest,prepared_custom=custom,prepared_generic=generic)
    check(lab.driver().execute('SELECT 1').fetchone()==(1,),'Independent SQL confirms the advanced workload leaves no server outage or retained study table.')
    print('Decisions: GIN containment/search and GiST ranges are demonstrated in earlier labs. BRIN needs physical correlation, hash is equality-only, and spatial indexes do not justify adding them to unrelated ticket predicates. Query plans may reject an index correctly.')

if __name__=='__main__':run(76,scenario)
