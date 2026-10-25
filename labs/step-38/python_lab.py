"""Ledger balance includes opening quantities, receipts, and corrections."""
import sys
from pathlib import Path
from uuid import UUID
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import event,select,func
from sqlalchemy.orm import Session
from college_maintenance.database import engine
from college_maintenance.migrations import upgrade
from college_maintenance.models import InventoryMovement
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed,client,headers

def scenario(lab):
    ids=seed(lab)
    with client(lab,ids) as api:
        def part(sku,opening,actor='super',cost='12.50'):
            return api.post('/parts',headers=headers(actor),json=dict(sku=sku,name='Synthetic part',unit_cost=cost,opening=opening))
        check(part('DENIED',1,actor='admin').status_code==403,'Department administration cannot change central inventory.')
        created=part('PART-1',3);check(created.status_code==201 and created.json()['stock_quantity']==3,'Initial positive stock creates a part and opening ledger entry together.')
        key=created.json()['id'];zero=part('PART-0',0).json()['id']
        check(part('BAD-COST',0,cost='1.001').status_code==400,'Excess monetary precision is rejected before scaled database conversion.')
        supplier=api.post('/suppliers',headers=headers('super'),json=dict(name='Synthetic supplier',contact='fictional@example.test')).json()['id']
        def move(**values):return api.post(f'/parts/{key}/movements',headers=headers('super'),json=values)
        check(move(kind='receipt',delta=2,supplier_id=supplier).json()['stock_quantity']==5,'A positive receipt requires an active supplier and increases balance.')
        check(move(kind='adjustment',delta=-1,reason='Count correction').json()['stock_quantity']==4,'A reasoned adjustment appends a signed delta.')
        check(move(kind='adjustment',delta=-5,reason='Too many').status_code==409,'A correction cannot make stock negative.')
        check(move(kind='adjustment',delta=1,reason=' ').status_code==400,'Corrections require a nonblank reason.')
        check(move(kind='receipt',delta=1).status_code==400,'Receipts cannot omit supplier provenance.')
        check(api.get('/parts',headers=headers('reporter')).status_code==403,'Student ticket access does not grant central catalog access.')
        check(api.get('/inventory/reconciliation',headers=headers('admin')).status_code==403,'Department staff cannot read the central movement ledger.')
        def fail(session,ctx,instances):
            if any(isinstance(row,InventoryMovement) for row in session.new):raise RuntimeError('synthetic ledger failure')
        event.listen(Session,'before_flush',fail)
        try:
            try:move(kind='receipt',delta=2,supplier_id=supplier)
            except RuntimeError:check(True,'A movement persistence failure propagates after the balance flush.')
            else:raise AssertionError('Movement failure swallowed')
        finally:event.remove(Session,'before_flush',fail)
        rows=api.get('/inventory/reconciliation',headers=headers('super')).json()
        check(len(rows)==2 and all(row['stock_quantity']==row['ledger_balance'] for row in rows),'Every stored balance reconciles, including zero stock with no ledger rows.')
    driver=lab.driver()
    check(driver.execute(f'SELECT stock_quantity,(SELECT sum(quantity_delta) FROM {lab.schema}.inventory_movements WHERE spare_part_id=%s) FROM {lab.schema}.spare_parts WHERE id=%s',(UUID(key),UUID(key))).fetchone()==(4,4),'An independent connection confirms failed ledger work did not leave a partial balance.')
    with lab.session() as s:
        check(s.scalar(select(func.count()).select_from(InventoryMovement).where(InventoryMovement.spare_part_id==UUID(zero)))==0,'Zero opening stock has no fabricated zero movement.')
    with engine.begin() as c:upgrade(c)

if __name__=='__main__':run(38,scenario)
