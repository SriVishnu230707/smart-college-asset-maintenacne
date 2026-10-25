"""Hand-counted multi-child costs expose fan-out and preserve historical scope."""
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from college_maintenance.attachments import FileStore,add_comment
from college_maintenance.completion import complete_work_order
from college_maintenance.inventory import create_part
from college_maintenance.models import Asset,SparePart
from college_maintenance.reads import scope_for_actor
from college_maintenance.repairs import edit_order
from college_maintenance.reports import costs_by_department_query,failure_frequency_query
from college_maintenance.workflow import transition_ticket
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed,client,headers
from labs.shared.repair_lab import prepare
from labs.shared.history_lab import install_guards

def scenario(lab):
    ids=seed(lab);install_guards(lab)
    with TemporaryDirectory(dir=Path(__file__).resolve().parents[2]/'.local') as directory:
        store=FileStore(directory)
        with lab.session() as s,s.begin():
            first=create_part(s,ids['super'],sku='REPORT-A',name='A',unit_cost='10.00',opening=10).id
            second=create_part(s,ids['super'],sku='REPORT-B',name='B',unit_cost='2.50',opening=10).id
        ticket_a,order_a=prepare(lab,ids,store,[(first,2),(second,4)],labor='5.00')
        ticket_b,order_b=prepare(lab,ids,store,[(first,1)],labor='7.00')
        complete_work_order(store,ids['tech'],order_a,session_factory=lab.session)
        complete_work_order(store,ids['tech'],order_b,session_factory=lab.session)
        ticket_c,order_c=prepare(lab,ids,store,labor='999.00')
        with lab.session() as s,s.begin():
            for number in range(3):add_comment(s,ids['reporter'],ticket_a,f'Comment {number}')
        observer=lab.driver()
        naive=observer.execute(f'''SELECT sum(w.labor_cost+p.quantity_used*p.unit_cost_at_use)
            FROM {lab.schema}.work_orders w JOIN {lab.schema}.work_order_parts p ON p.work_order_id=w.id
            LEFT JOIN {lab.schema}.ticket_comments c ON c.ticket_id=w.ticket_id WHERE w.status='completed' ''').fetchone()[0]
        check(naive==Decimal('137.00'),'The naive parts/comments join multiplies labor and parts into an incorrect 137.00 total.')
        sql=f'''WITH parts AS (SELECT work_order_id,sum(quantity_used*unit_cost_at_use) AS cost FROM {lab.schema}.work_order_parts GROUP BY work_order_id),
            orders AS (SELECT w.id,t.department_id,w.labor_cost+coalesce(p.cost,0) AS cost FROM {lab.schema}.work_orders w
                JOIN {lab.schema}.maintenance_tickets t ON t.id=w.ticket_id LEFT JOIN parts p ON p.work_order_id=w.id WHERE w.status='completed')
            SELECT d.code,coalesce(sum(o.cost),0) FROM {lab.schema}.departments d LEFT JOIN orders o ON o.department_id=d.id GROUP BY d.id,d.code ORDER BY d.code'''
        raw=observer.execute(sql).fetchall()
        check(raw==[('CSE',Decimal('52.00')),('ECE',0)],'Pre-aggregated SQL matches the hand-counted 35.00 plus 17.00, including an empty department.')
        with lab.session() as s:
            scope=scope_for_actor(s,ids['super']);rows=s.execute(costs_by_department_query(scope)).all()
            check([(row.code,row.total_cost) for row in rows]==raw,'The SQLAlchemy expression agrees with raw SQL at one row per recorded department.')
            check(rows[0].completed_orders==2,'Unfinished labor estimates are excluded from historical completed cost and repair counts.')
            failures=s.execute(failure_frequency_query(scope)).all()
            check(len(failures)==1 and failures[0].ticket_count==3,'Failure frequency counts three reports once each, independently of parts, comments and repair rows.')
        with lab.session() as s,s.begin():
            edit_order(s,ids['tech'],order_c,labor_cost='0.00',completion_note='Labor-only repair')
        complete_work_order(store,ids['tech'],order_c,session_factory=lab.session)
        with lab.session() as s,s.begin():
            for key in (ticket_a,ticket_b,ticket_c):transition_ticket(s,ids['admin'],key,action='verify',reason='Verified')
            # The isolated transfer fixture satisfies the all-terminal prerequisite.
            s.get(Asset,ids['asset']).department_id=ids['other_dept']
            s.get(SparePart,first).current_unit_cost='99.99'
        with client(lab,ids,storage=store) as api:
            costs=api.get('/reports/costs',headers=headers('admin'))
            check(costs.status_code==200 and len(costs.json())==1 and costs.json()[0]['total_cost']=='52.00','Historical department costs survive eligible asset transfer and current price changes.')
            check(costs.json()[0]['completed_orders']==3,'A completed zero-cost labor-only repair counts as a repair without altering money totals.')
            other=api.get('/reports/costs',headers=headers('other_admin')).json()
            check(len(other)==1 and other[0]['code']=='ECE' and other[0]['total_cost']=='0.00','Receiving an asset does not move its original department repair history.')
            check(api.get('/reports/costs',headers=headers('reporter')).status_code==403,'Reporter ticket history access does not expose cost reports.')
            check(api.get('/reports/failures',headers=headers('other_admin')).json()==[],'Failure frequency uses recorded ticket department rather than current asset ownership.')

if __name__=='__main__':run(49,scenario)
