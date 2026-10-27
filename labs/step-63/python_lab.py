from pathlib import Path
from tempfile import TemporaryDirectory
import shutil,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import text
from college_maintenance.attachments import FileStore
from college_maintenance.inventory import create_part
from college_maintenance.completion import complete_work_order
from college_maintenance.models import WorkOrderAttachment
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed
from labs.shared.repair_lab import prepare
from labs.shared.history_lab import install_guards
from labs.shared.recovery_lab import restored_database

def scenario(lab):
    ids=seed(lab);install_guards(lab)
    with TemporaryDirectory(dir=Path(__file__).resolve().parents[2]/'.local') as directory:
        store=FileStore(Path(directory)/'original')
        with lab.session() as s,s.begin():part=create_part(s,ids['super'],sku='BACKUP',name='Recovery part',unit_cost='7.50',opening=3).id
        ticket,order=prepare(lab,ids,store,[(part,2)],labor='5.00')
        complete_work_order(store,ids['tech'],order,session_factory=lab.session)
        shutil.copytree(store.root,Path(directory)/'restored-files')
        with restored_database(lab) as target:
            with target.connect() as c:
                check(c.scalar(text(f'SELECT stock_quantity FROM {lab.schema}.spare_parts'))==1,'A real custom-format dump restores consumed stock into a different fresh database.')
                balance=c.execute(text(f'SELECT p.stock_quantity,sum(m.quantity_delta) FROM {lab.schema}.spare_parts p JOIN {lab.schema}.inventory_movements m ON m.spare_part_id=p.id GROUP BY p.id')).one()
                check(balance==(1,1),'Opening and consumption movements reconcile after restoration.')
                cost=c.scalar(text(f'SELECT w.labor_cost+sum(p.quantity_used*p.unit_cost_at_use) FROM {lab.schema}.work_orders w JOIN {lab.schema}.work_order_parts p ON p.work_order_id=w.id GROUP BY w.id'))
                check(cost==20,'Historical labor and frozen part costs survive backup/restore exactly.')
                check(c.scalar(text(f'SELECT count(*) FROM {lab.schema}.audit_events WHERE action=\'work_order_completed\''))==1,'The completion audit event survives with its original relationships.')
                metadata=c.execute(text(f'SELECT storage_key,size,sha256 FROM {lab.schema}.work_order_attachments')).mappings().one()
                from types import SimpleNamespace
                check(FileStore(Path(directory)/'restored-files').read(SimpleNamespace(**metadata))==b'synthetic completion proof','Separately restored attachment bytes match the restored database metadata digest.')
            try:
                with target.begin() as c:c.execute(text(f'UPDATE {lab.schema}.work_orders SET labor_cost=999 WHERE id=:id'),{'id':order})
            except Exception as exc:
                check(getattr(getattr(exc,'orig',None),'sqlstate',None)=='23514','Restored trigger definitions still reject edits to completed historical facts.')
            else:raise AssertionError('Restored history guard missing')
        check(lab.driver().execute(f'SELECT stock_quantity FROM {lab.schema}.spare_parts').fetchone()[0]==1,'Restoring and dropping the scratch database leaves the source data untouched.')
    print('Coverage: schema/data/functions/triggers and separate local files. Roles and server settings are provisioned separately; a single-database dump is not a cluster backup or PITR claim.')

if __name__=='__main__':run(63,scenario)
