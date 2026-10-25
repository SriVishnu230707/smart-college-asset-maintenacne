"""Synthetic identities and HTTP helpers shared by workflow proofs."""
from fastapi.testclient import TestClient
from college_maintenance.api import create_app
from college_maintenance.models import Asset, User

def seed(lab):
    ids = lab.seed()
    with lab.session() as session, session.begin():
        for name, role, department in [('admin','department_admin',ids['dept']), ('other_admin','department_admin',ids['other_dept']),
            ('super','super_admin',None), ('other_tech','technician',ids['other_dept'])]:
            user = User(email=f'{name}@example.test', display_name=name, password_hash='synthetic_only', role=role, department_id=department)
            session.add(user); session.flush(); ids[name] = user.id
        asset = Asset(asset_code='OTHER-001', name='Other asset', department_id=ids['other_dept'], category_id=ids['category'])
        session.add(asset); session.flush(); ids['other_asset'] = asset.id
    return ids

def client(lab, ids, **options):
    return TestClient(create_app(session_factory=lab.session, authenticate=lambda token: ids.get(token), **options))

def headers(name): return {'Authorization':f'Bearer {name}'}

def report(client, ids, actor='reporter', **values):
    return client.post('/tickets', headers=headers(actor), json=dict(asset_id=str(ids['asset']), title='Broken computer', description='Synthetic issue', **values))
