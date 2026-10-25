"""Bidirectional relationship synchronization versus installed foreign keys."""
import sys
from pathlib import Path
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from college_maintenance.models import Asset, Department
from labs.shared.orm_lab import check, run

def scenario(lab):
    ids=lab.seed()
    with lab.session() as s,s.begin():
        department=Department(code='MECH',name='Mechanical')
        asset=Asset(asset_code='REL-001',name='Relationship Computer',category_id=ids['category'],department=department)
        check(asset in department.assets and asset.department is department,'Assigning the scalar relationship synchronizes its collection before any SQL.')
        s.add(asset)
        check(asset in s.new and department in s.new,'Default save-update cascade enlists the new related department.')
        s.flush(); asset_id=asset.id; department_id=department.id
        check(asset.department_id==department_id,'Flush orders related INSERTs and synchronizes the generated foreign-key value.')
    with lab.session() as s,s.begin():
        loaded=s.get(Asset,asset_id)
        check(loaded.department.code=='MECH' and loaded in loaded.department.assets,'Both navigation directions load the committed relationship.')
        original=loaded.department
        destination=s.get(Department,ids['dept'])
        loaded.department=destination
        check(loaded not in original.assets and loaded in destination.assets,'Reassigning the scalar synchronizes both loaded collections.')
        s.flush()
        check(loaded.department_id==ids['dept'],'Flush persists the changed reference on the child row.')
    with lab.engine.begin() as c:
        try:
            with c.begin_nested():
                c.execute(text(f'UPDATE {lab.schema}.assets SET department_id=:bad WHERE id=:id'),{'bad':uuid4(),'id':asset_id})
        except IntegrityError as exc:
            check(exc.orig.sqlstate=='23503' and exc.orig.diag.constraint_name=='fk_assets_department','Direct SQL still enforces the foreign key without any ORM navigation.')
        else: raise AssertionError('The database accepted an absent parent')
    relationship=inspect(Asset).relationships['department']
    check(not relationship.uselist and inspect(Department).relationships['assets'].uselist,'Typing configures a scalar parent and a collection of children.')
    check(not Asset.__table__.c.department_id.nullable and relationship.back_populates=='assets','Database nullability and ORM synchronization are separate explicit declarations.')
    with lab.session() as s:
        check(s.get(Asset,asset_id).department.code=='CSE' and not s.get(Department,department_id).assets,'A fresh reader confirms the moved child and the empty original collection.')

if __name__=='__main__': run(22,scenario)
