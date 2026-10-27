from pathlib import Path
from uuid import UUID
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy.exc import DBAPIError
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed
from labs.shared.performance_lab import explain,nodes,save_plans
from labs.shared.recovery_lab import restored_database

def scenario(lab):
    seed(lab);schema=lab.schema
    try:
        with lab.engine.begin() as c:
            c.exec_driver_sql(f'CREATE TABLE {schema}.partitioned_audit(event_date date NOT NULL,event_id uuid NOT NULL,action text NOT NULL,PRIMARY KEY(event_date,event_id)) PARTITION BY RANGE(event_date)')
            c.exec_driver_sql(f"CREATE TABLE {schema}.audit_oct PARTITION OF {schema}.partitioned_audit FOR VALUES FROM ('2026-10-01') TO ('2026-11-01')")
            c.exec_driver_sql(f"CREATE TABLE {schema}.audit_nov PARTITION OF {schema}.partitioned_audit FOR VALUES FROM ('2026-11-01') TO ('2026-12-01')")
            c.exec_driver_sql(f"INSERT INTO {schema}.partitioned_audit SELECT date '2026-10-01'+(i%%61),gen_random_uuid(),'synthetic event' FROM generate_series(1,20000) i")
            c.exec_driver_sql(f'ANALYZE {schema}.partitioned_audit')
            plan=explain(c,f"SELECT count(*) FROM {schema}.partitioned_audit WHERE event_date>=date '2026-10-01' AND event_date<date '2026-11-01'")
            relations={node['Relation Name'] for node in nodes(plan['Plan']) if 'Relation Name' in node}
            check(relations=={'audit_oct'},'The October predicate prunes the November partition in an actual execution plan.')
            unbounded=explain(c,f'SELECT count(*) FROM {schema}.partitioned_audit')
            check({n['Relation Name'] for n in nodes(unbounded['Plan']) if 'Relation Name' in n}=={'audit_oct','audit_nov'},'A query without a partition-key restriction must visit both child relations.')
            try:
                with c.begin_nested():c.exec_driver_sql(f'CREATE UNIQUE INDEX invalid_global_identity ON {schema}.partitioned_audit(event_id)')
            except DBAPIError as exc:check(exc.orig.sqlstate=='0A000','Global uniqueness cannot omit the partition key from this partitioned-table unique index.')
            else:raise AssertionError('Invalid global uniqueness allowed')
            identity=UUID(int=77)
            c.exec_driver_sql(f"INSERT INTO {schema}.partitioned_audit VALUES('2026-10-01',%s,'Identity example'),('2026-11-01',%s,'Identity example')",(identity,identity))
            check(c.exec_driver_sql(f'SELECT count(*) FROM {schema}.partitioned_audit WHERE event_id=%s',(identity,)).scalar_one()==2,'The composite key permits the same event UUID on different dates; uniqueness policy is explicit.')
            october=c.exec_driver_sql(f'SELECT count(*) FROM {schema}.audit_oct').scalar_one()
            c.exec_driver_sql(f'ALTER TABLE {schema}.partitioned_audit DETACH PARTITION {schema}.audit_oct')
            check(c.exec_driver_sql(f"SELECT count(*) FROM {schema}.partitioned_audit WHERE event_date<date '2026-11-01'").scalar_one()==0,'Detaching a partition removes its rows from parent queries without deleting the archive table.')
            check(c.exec_driver_sql(f'SELECT count(*) FROM {schema}.audit_oct').scalar_one()==october,'The detached relation retains every archived row for the explicit retention/recovery policy.')
            c.exec_driver_sql(f"ALTER TABLE {schema}.partitioned_audit ATTACH PARTITION {schema}.audit_oct FOR VALUES FROM ('2026-10-01') TO ('2026-11-01')")
            save_plans(77,pruned=plan,all_partitions=unbounded)
        with restored_database(lab,77) as target:
            with target.connect() as c:
                check(c.exec_driver_sql(f'SELECT count(*) FROM {schema}.partitioned_audit').scalar_one()==20002,'Real dump/restore preserves all rows after reattachment.')
                check(c.exec_driver_sql('SELECT count(*) FROM pg_inherits WHERE inhparent=to_regclass(%s)',(schema+'.partitioned_audit',)).scalar_one()==2,'Restoration recreates the partition hierarchy, not just flattened data.')
        check(lab.driver().execute(f'SELECT count(*) FROM {schema}.partitioned_audit').fetchone()[0]==20002,'Independent source observation confirms recovery did not mutate the original partitioned data.')
    finally:
        with lab.engine.begin() as c:
            for table in ('partitioned_audit','audit_oct','audit_nov'):c.exec_driver_sql(f'DROP TABLE IF EXISTS {schema}.{table}')
    print('Decision: keep the ordinary base audit table until retention/volume evidence justifies partitioning. Partition removal is a retention decision, not an automatic backup.')

if __name__=='__main__':run(77,scenario)
