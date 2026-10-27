"""Disposable realistic workload; plans are evidence, timings are not thresholds."""
from contextlib import contextmanager
import json,os
from pathlib import Path

@contextmanager
def workload(lab, rows=40000):
    assert 1000<=rows<=200000
    with lab.engine.begin() as c:
        c.exec_driver_sql('CREATE TEMP TABLE bench_tickets(id int PRIMARY KEY,department int NOT NULL,status text NOT NULL,created_at timestamptz NOT NULL,title text NOT NULL) ON COMMIT DROP')
        c.exec_driver_sql("INSERT INTO bench_tickets SELECT i,i%%20,CASE WHEN i%%101=0 THEN 'open' ELSE 'closed' END,timestamptz '2026-01-01 UTC'+i*interval '1 minute',repeat('synthetic issue ',8) FROM generate_series(1,%s) i",(rows,))
        c.exec_driver_sql('ANALYZE bench_tickets')
        yield c

def explain(c, query, parameters=()):
    return c.exec_driver_sql('EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) '+query,parameters).scalar_one()[0]

def nodes(plan):
    yield plan
    for child in plan.get('Plans',[]):yield from nodes(child)

def save_plans(step, **plans):
    path=Path(__file__).resolve().parents[1]/f'step-{step}'/'plans.json'
    if path.exists() and os.environ.get('COLLEGE_CAPTURE_PLANS')!='1':return
    path.write_text(json.dumps(plans,indent=2,default=str)+'\n',encoding='utf-8')

QUEUE="SELECT id,title FROM bench_tickets WHERE department=7 AND status='open' ORDER BY created_at DESC,id DESC LIMIT 20"
