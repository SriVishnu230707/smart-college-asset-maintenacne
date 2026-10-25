"""Exercise HTTP identity, validation, scoped reads, and resource cleanup."""
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fastapi.testclient import TestClient
from sqlalchemy import event
from college_maintenance.api import create_app
from college_maintenance.authentication import authenticate_token
from college_maintenance.database import engine
from college_maintenance.models import MaintenanceTicket, User
from labs.shared.orm_lab import check, run

def scenario(lab):
    ids = lab.seed()
    with lab.session() as session, session.begin():
        ticket = MaintenanceTicket(asset_id=ids['asset'], department_id=ids['dept'], reported_by_id=ids['reporter'], title='API fixture', description='API fixture', priority='high')
        session.add(ticket); session.flush(); ticket_id = ticket.id
    app = create_app(session_factory=lab.session, authenticate=lambda token: ids['reporter'] if token == 'synthetic-bearer' else None)
    headers = {'Authorization':'Bearer synthetic-bearer'}
    commits = []
    def committed(connection): commits.append(True)
    event.listen(engine, 'commit', committed)
    try:
        with TestClient(app) as client:
            check(client.get('/tickets').status_code == 401, 'A missing bearer credential is rejected before database access.')
            check(client.get('/tickets', headers={'Authorization':'Bearer invalid'}).status_code == 401, 'Invalid bearer credentials do not select an actor.')
            response = client.get(f'/tickets/{ticket_id}', headers=headers)
            check(response.status_code == 200 and response.json()['title'] == 'API fixture', 'A verified actor can read an authorized ticket through the real HTTP boundary.')
            check(len(commits) == 1, 'The successful read has exactly one explicit transaction owner.')
            check('password' not in response.text and 'email' not in response.text, 'Response construction excludes private user attributes.')
            check(client.get('/tickets/not-a-uuid', headers=headers).status_code == 422, 'Malformed path input fails at request validation.')
            check(client.get('/tickets?limit=0', headers=headers).status_code == 422, 'Invalid page bounds fail at request validation.')
            check(client.get('/tickets?status=unknown', headers=headers).status_code == 400, 'Unsupported domain filters fail in the read layer.')
            check(client.get('/assets/00000000-0000-0000-0000-000000000000', headers=headers).status_code == 404, 'An absent resource returns the documented not-found response.')
            check(client.get('/tickets', headers={**headers,'X-Role':'super_admin'}).json()['items'][0]['id'] == str(ticket_id), 'Client role headers do not control the authenticated actor.')
            with lab.session() as session, session.begin(): session.get(User, ids['reporter']).is_active = False
            check(client.get('/tickets', headers=headers).status_code == 403, 'An authenticated but inactive database actor is denied.')
    finally: event.remove(engine, 'commit', committed)
    check(engine.pool.checkedout() == 0 and all(not s.in_transaction() for s in lab.sessions), 'Success, validation failures, and domain failures return every request connection.')
    previous = os.environ.get('COLLEGE_API_TOKENS_FILE')
    with TemporaryDirectory(dir=Path(__file__).resolve().parents[2]/'.local') as directory:
        path = Path(directory)/'tokens.json'; os.environ['COLLEGE_API_TOKENS_FILE'] = str(path)
        token = 'synthetic-test-credential-only'
        path.write_text(json.dumps({hashlib.sha256(token.encode()).hexdigest(): {'actor_id':str(ids['reporter']), 'expires_at':(datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()}}))
        try:
            check(authenticate_token(token) == ids['reporter'] and authenticate_token('wrong') is None, 'The default verifier resolves opaque token digests and fails closed for unknown credentials.')
            path.write_text('{}')
            check(authenticate_token(token) is None, 'Removing a locally provisioned credential revokes it without accepting an actor ID.')
        finally:
            if previous is None: os.environ.pop('COLLEGE_API_TOKENS_FILE', None)
            else: os.environ['COLLEGE_API_TOKENS_FILE'] = previous

if __name__ == '__main__': run(33, scenario)
