"""Local simulated consumer: no email, webhook or third-party message is sent."""
from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import datetime,timezone
from uuid import UUID
import json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import select,func,DateTime,text
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column
from sqlalchemy.dialects.postgresql import JSONB,insert
from college_maintenance.attachments import FileStore
from college_maintenance.completion import complete_in_session
from college_maintenance.inventory import create_part
from college_maintenance.models import InventoryMovement
from labs.shared.orm_lab import check,run
from labs.shared.workflow_lab import seed
from labs.shared.repair_lab import prepare
from labs.shared.history_lab import install_guards
from labs.shared.extensions_lab import extra_tables
from labs.shared.concurrency_lab import independent_factory

class Mapping(DeclarativeBase):pass
class Envelope(Mapping):
    __tablename__='outbox_envelopes'
    id:Mapped[UUID]=mapped_column(primary_key=True)
    payload:Mapped[dict]=mapped_column(JSONB)
    delivered_at:Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
class Receipt(Mapping):
    __tablename__='consumer_receipts'
    id:Mapped[UUID]=mapped_column(primary_key=True)
    payload:Mapped[dict]=mapped_column(JSONB)

def produce(session,store,actor,order,fault=None):
    result=complete_in_session(session,store,actor,order,_fault=fault)
    session.execute(insert(Envelope).values(id=order,payload=json.loads(json.dumps(result,default=str))).on_conflict_do_nothing(index_elements=[Envelope.id]))
    return result

def scenario(lab):
    ids=seed(lab);install_guards(lab)
    with extra_tables(lab,Mapping.metadata),TemporaryDirectory(dir=Path(__file__).resolve().parents[2]/'.local') as directory:
        store=FileStore(directory)
        with lab.session() as s,s.begin():part=create_part(s,ids['super'],sku='OUTBOX',name='Part',unit_cost='10.00',opening=2).id
        _,order=prepare(lab,ids,store,[(part,1)])
        with lab.session() as s,s.begin():original=produce(s,store,ids['tech'],order)
        with lab.session() as s,s.begin():check(produce(s,store,ids['tech'],order)==original,'Producer retries preserve the existing completion and unique event identity.')
        _,failed_order=prepare(lab,ids,store,[(part,1)])
        try:
            with lab.session() as s,s.begin():
                def fault(stage):
                    if stage=='after_ledger':raise RuntimeError('injected producer failure')
                produce(s,store,ids['tech'],failed_order,fault)
        except RuntimeError:pass
        with lab.session() as s:check(s.scalar(select(func.count()).select_from(Envelope))==1,'Only the committed repair publishes an envelope; failed repair writes and its event roll back together.')
        pick=select(Envelope).where(Envelope.delivered_at.is_(None)).order_by(Envelope.id).with_for_update(skip_locked=True).limit(1)
        with independent_factory(lab) as factory:
            with factory() as owner,owner.begin():
                check(owner.scalar(pick).id==order,'A publisher locks one committed, undelivered envelope.')
                with factory() as other,other.begin():check(other.scalar(pick) is None,'SKIP LOCKED lets another publisher avoid duplicate simultaneous work without waiting.')
            backends=[]
            def deliver(crash=False):
                with factory() as publisher,publisher.begin():
                    event=publisher.scalar(pick)
                    if event is None:return None
                    first=publisher.scalar(text('SELECT pg_backend_pid()'))
                    with factory() as consumer,consumer.begin():
                        second=consumer.scalar(text('SELECT pg_backend_pid()'))
                        applied=consumer.scalar(insert(Receipt).values(id=event.id,payload=event.payload).on_conflict_do_nothing(index_elements=[Receipt.id]).returning(Receipt.id))
                    backends.append((first,second))
                    if crash:raise RuntimeError('Consumer committed; publisher crashed before acknowledgement')
                    event.delivered_at=datetime.now(timezone.utc)
                    return applied is not None
            try:deliver(crash=True)
            except RuntimeError:check(True,'The simulated crash occurs after independent consumer commit but before publisher acknowledgement.')
            with lab.session() as s:check(s.get(Envelope,order).delivered_at is None and s.scalar(select(func.count()).select_from(Receipt))==1,'The event remains retryable while the consumer side effect is already durable.')
            check(deliver() is False,'Redelivery is acknowledged without applying a second consumer effect because its receipt key is unique.')
            check(deliver() is None,'An acknowledged envelope is not selected again.')
            check(all(a!=b for a,b in backends),'Publisher and consumer use distinct committed transactions and physical connections.')
        observer=lab.driver()
        check(observer.execute(f'SELECT count(*) FROM {lab.schema}.consumer_receipts').fetchone()[0]==1,'Independent SQL observes exactly one simulated consumer effect across crash and redelivery.')
        check(observer.execute(f"SELECT count(*) FROM {lab.schema}.inventory_movements WHERE kind='consume'").fetchone()[0]==1,'Outbox delivery retries do not repeat the business stock transaction.')
    print('This optional outbox prototype uses at-least-once delivery and an idempotent local consumer. No third-party messages are sent, and no exactly-once guarantee is claimed for arbitrary external services. Receipt storage intentionally has no cross-consumer foreign key to a publisher-locked row.')

if __name__=='__main__':run(79,scenario)
