"""Separate Python identity, transaction-visible freshness, and merge writes."""
import sys
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import DetachedInstanceError
from college_maintenance.models import Asset
from labs.shared.orm_lab import check, run


def scenario(lab):
    ids=lab.seed()
    other=lab.driver()
    with lab.session() as s:
        before=len(lab.kinds('assets'))
        first=s.get(Asset,ids['asset']); second=s.get(Asset,ids['asset'])
        check(first is second and len(lab.kinds('assets'))==before+1,'Repeated get returns the same Python object with one SELECT.')
        other.execute(f'UPDATE {lab.schema}.assets SET location=%s WHERE id=%s',('External Lab',ids['asset']))
        check(s.get(Asset,ids['asset']) is first and first.location=='Original Lab','The identity map retains loaded values after another connection commits.')
        before=len(lab.kinds('assets'))
        s.expire(first,['location'])
        check(len(lab.kinds('assets'))==before and 'location' in inspect(first).expired_attributes,'Expire marks the attribute without issuing SQL.')
        check(first.location=='External Lab' and len(lab.kinds('assets'))==before+1,'Access after expire reloads the independently committed value.')
        other.execute(f'UPDATE {lab.schema}.assets SET location=%s WHERE id=%s',('Refresh Lab',ids['asset']))
        s.refresh(first,['location'])
        check(first.location=='Refresh Lab','Refresh performs an immediate database reload.')
        s.commit()
        check(inspect(first).expired,'Default commit expires loaded attributes while retaining the identity marker.')
    try:
        _=first.location
    except DetachedInstanceError:
        check(inspect(first).detached,'An expired detached object cannot load values without a Session.')
    else:
        raise AssertionError('Expired detached access unexpectedly loaded')
    first.location='Merged Lab'
    with lab.session() as s,s.begin():
        merged=s.merge(first)
        check(merged is not first and inspect(merged).persistent and inspect(first).detached,'Merge copies state into a managed target rather than attaching the source.')
        check(merged.location=='Merged Lab','Loaded source values are copied to the merge target.')
    with lab.session() as s:
        check(s.get(Asset,ids['asset']).location=='Merged Lab','A fresh Session confirms the committed merge update.')
    new_id=uuid4()
    source=Asset(id=new_id,asset_code='MERGE-NEW',name='New merge',department_id=ids['dept'],category_id=ids['category'])
    with lab.session() as s,s.begin():
        target=s.merge(source)
        check(inspect(target).pending and inspect(source).transient,'Merge of a missing identity can produce a pending INSERT target.')
    race_id=uuid4()
    try:
        with lab.session() as s:
            source=Asset(id=race_id,asset_code='RACE-LOSER',name='Losing merge',department_id=ids['dept'],category_id=ids['category'])
            s.merge(source)
            other.execute(f'INSERT INTO {lab.schema}.assets (id,asset_code,name,department_id,category_id) VALUES (%s,%s,%s,%s,%s)',
                          (race_id,'RACE-WINNER','Independent winner',ids['dept'],ids['category']))
            s.flush()
    except IntegrityError as exc:
        check(exc.orig.sqlstate=='23505' and exc.orig.diag.constraint_name=='pk_assets','A concurrent insert defeats merge with a primary-key conflict; merge is not atomic upsert.')
    else:
        raise AssertionError('The merge race was not rejected')
    with lab.session() as s:
        check(s.get(Asset,race_id).asset_code=='RACE-WINNER' and s.get(Asset,new_id).asset_code=='MERGE-NEW',
              'The independent winner and previously committed merge insertion survive the failed merge.')


if __name__=='__main__': run(21,scenario)
