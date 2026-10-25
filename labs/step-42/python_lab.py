"""Controlled independent connections distinguish MVCC from identity-map state."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import select
from college_maintenance.models import Asset
from labs.shared.orm_lab import check,run

def scenario(lab):
    ids=lab.seed();first=lab.driver();second=lab.driver()
    check(first.execute('SELECT pg_backend_pid()').fetchone()!=second.execute('SELECT pg_backend_pid()').fetchone(),'Visibility experiments use two physical PostgreSQL backend connections.')
    sql=f'SELECT location FROM {lab.schema}.assets WHERE id=%s'
    update=f'UPDATE {lab.schema}.assets SET location=%s WHERE id=%s'
    with lab.session() as session:
        cached=session.get(Asset,ids['asset'])
        first.execute('BEGIN ISOLATION LEVEL READ COMMITTED')
        check(first.execute("SHOW transaction_isolation").fetchone()[0]=='read committed','The reader transaction explicitly uses READ COMMITTED.')
        check(first.execute(sql,(ids['asset'],)).fetchone()[0]=='Original Lab','The first statement sees the committed starting location.')
        second.execute('BEGIN');second.execute(update,('Committed change',ids['asset']))
        check(first.execute(sql,(ids['asset'],)).fetchone()[0]=='Original Lab','A different connection cannot dirty-read an uncommitted update.')
        check(second.execute(sql,(ids['asset'],)).fetchone()[0]=='Committed change','A writer sees its own uncommitted value.')
        second.execute('COMMIT')
        check(first.execute(sql,(ids['asset'],)).fetchone()[0]=='Committed change','The next statement in the same READ COMMITTED transaction sees the newly committed version.')
        check(cached.location=='Original Lab','The ORM identity map can retain an older Python value independently of PostgreSQL visibility.')
        projected=session.scalar(select(Asset.location).where(Asset.id==ids['asset']))
        check(projected=='Committed change' and cached.location=='Original Lab','A SQL projection sees fresh committed data without automatically overwriting an existing entity attribute.')
        session.refresh(cached)
        check(cached.location=='Committed change','Explicit refresh updates the identity-mapped Python attribute.')
        first.execute(update,('Uncommitted second change',ids['asset']))
        check(second.execute(sql,(ids['asset'],)).fetchone()[0]=='Committed change','A competing reader still sees the prior committed version while the first writer is open.')
        first.execute('ROLLBACK')
        check(second.execute(sql,(ids['asset'],)).fetchone()[0]=='Committed change','Rolling back the writer preserves the previous committed location.')
    check(first.info.transaction_status.name==second.info.transaction_status.name=='IDLE','Both independent experiments finish without idle transactions.')

if __name__=='__main__':run(42,scenario)
