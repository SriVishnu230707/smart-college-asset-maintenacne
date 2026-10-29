"""Dashboard HTTP acceptance tests against a disposable real PostgreSQL schema.

Run: .venv/Scripts/python.exe -m unittest tests.dashboard_cases -v
"""
import unittest
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.schema import CreateSchema, DropSchema

from college_maintenance.database import engine
from college_maintenance.models import Asset, Base, MaintenanceTicket
from labs.shared.orm_lab import Lab
from labs.shared.workflow_lab import client, headers, report, seed


class DashboardAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lab = Lab('ui_' + uuid4().hex, uuid4())
        cls.addClassCleanup(cls.cleanup_schema)
        with cls.lab.engine.begin() as connection:
            connection.execute(CreateSchema(cls.lab.schema))
            Base.metadata.create_all(connection)
        cls.ids = seed(cls.lab)
        cls.api = client(cls.lab, cls.ids)
        cls.addClassCleanup(cls.api.close)
        for number in range(25):
            response = report(cls.api, cls.ids, priority='critical' if number == 0 else 'medium')
            if response.status_code != 201:
                raise AssertionError(response.text)
        other = cls.api.post('/tickets', headers=headers('other'), json={
            'asset_id': str(cls.ids['other_asset']), 'title': 'Other department issue',
            'description': 'Must remain scoped', 'priority': 'high'})
        if other.status_code != 201:
            raise AssertionError(other.text)
        cls.other_ticket = other.json()['id']
        with cls.lab.session() as session, session.begin():
            for number in range(35):
                session.add(Asset(asset_code=f'DASH-{number:03}', name=f'Study Asset {number}',
                                  department_id=cls.ids['dept'], category_id=cls.ids['category']))

    @classmethod
    def cleanup_schema(cls):
        for session in cls.lab.sessions:
            session.close()
        with cls.lab.engine.begin() as connection:
            connection.execute(DropSchema(cls.lab.schema, cascade=True))
        with engine.connect() as connection:
            assert connection.scalar(select(func.to_regnamespace(cls.lab.schema))) is None
        engine.dispose()

    def test_page_and_static_files_have_no_auth_or_external_dependencies(self):
        page = self.api.get('/')
        self.assertEqual(page.status_code, 200)
        self.assertIn('Campus Care', page.text)
        self.assertIn("script-src 'self'", page.headers['content-security-policy'])
        self.assertEqual(page.headers['cache-control'], 'no-store')
        for path in ['/static/app.js', '/static/styles.css']:
            self.assertEqual(self.api.get(path).status_code, 200)
        self.assertEqual(self.api.get('/static/../authentication.py').status_code, 404)

    def test_data_routes_require_authentication(self):
        for path in ['/me', '/dashboard/summary', '/assets', '/dashboard/technicians']:
            with self.subTest(path=path):
                self.assertEqual(self.api.get(path).status_code, 401)

    def test_identity_comes_from_database(self):
        result = self.api.get('/me', headers=headers('reporter')).json()
        self.assertEqual(result['role'], 'student')
        self.assertEqual(result['department'], 'Computer Science')
        self.assertEqual(set(result), {'id', 'name', 'role', 'department'})
        self.assertEqual(self.api.get('/me', headers=headers('super')).json()['department'], 'All departments')

    def test_summary_counts_all_visible_tickets_not_only_first_page(self):
        first = self.api.get('/tickets?limit=20', headers=headers('reporter')).json()
        self.assertEqual(len(first['items']), 20)
        self.assertTrue(first['next_cursor'])
        summary = self.api.get('/dashboard/summary', headers=headers('reporter')).json()
        self.assertGreaterEqual(summary['total'], 25)
        with self.lab.session() as session:
            expected = session.scalar(select(func.count()).select_from(MaintenanceTicket).where(
                MaintenanceTicket.reported_by_id == self.ids['reporter']))
        self.assertEqual(summary['total'], expected)
        self.assertEqual(summary['urgent'], 1)

    def test_summary_department_and_technician_scope(self):
        other = self.api.get('/dashboard/summary', headers=headers('other_admin')).json()
        self.assertEqual(other['total'], 1)
        self.assertEqual(other['urgent'], 1)
        self.assertEqual(self.api.get('/dashboard/summary', headers=headers('other_tech')).json()['total'], 0)
        total = self.api.get('/dashboard/summary', headers=headers('super')).json()['total']
        own = self.api.get('/dashboard/summary', headers=headers('reporter')).json()['total']
        self.assertEqual(total, own + 1)

    def test_asset_discovery_scope_and_literal_wildcards(self):
        assets = self.api.get('/assets?limit=100', headers=headers('reporter')).json()['items']
        self.assertNotIn(str(self.ids['other_asset']), {asset['id'] for asset in assets})
        self.assertEqual(len(self.api.get('/assets?q=lab', headers=headers('reporter')).json()['items']), 1)
        self.assertEqual(self.api.get('/assets?q=%25', headers=headers('reporter')).json()['items'], [])
        self.assertEqual(len(self.api.get('/assets?q=OTHER', headers=headers('super')).json()['items']), 1)

    def test_asset_pages_have_stable_order_without_duplicates(self):
        first = self.api.get('/assets?limit=20', headers=headers('reporter')).json()
        second = self.api.get(f"/assets?limit=20&offset={first['next_offset']}", headers=headers('reporter')).json()
        ids = [asset['id'] for page in [first, second] for asset in page['items']]
        self.assertEqual(len(ids), 36)
        self.assertEqual(len(set(ids)), 36)
        self.assertIsNone(second['next_offset'])

    def test_bounded_asset_parameters(self):
        for query in ['limit=101', 'limit=0', 'offset=-1', 'q=' + 'x'*151]:
            self.assertEqual(self.api.get('/assets?' + query, headers=headers('reporter')).status_code, 422)

    def test_technician_directory_does_not_leak_other_departments(self):
        self.assertEqual(self.api.get('/dashboard/technicians', headers=headers('reporter')).status_code, 403)
        rows = self.api.get('/dashboard/technicians', headers=headers('admin')).json()
        self.assertEqual({row['id'] for row in rows}, {str(self.ids['tech'])})
        self.assertEqual(len(self.api.get('/dashboard/technicians', headers=headers('super')).json()), 2)
        query = '/dashboard/technicians?department_id=' + str(self.ids['other_dept'])
        self.assertEqual(self.api.get(query, headers=headers('admin')).json(), [])
        self.assertEqual({row['id'] for row in self.api.get(query, headers=headers('super')).json()}, {str(self.ids['other_tech'])})
        self.assertEqual(self.api.get('/dashboard/technicians?department_id=invalid', headers=headers('super')).status_code, 422)

    def test_rejected_urgent_tickets_are_not_counted_as_active(self):
        response = report(self.api, self.ids, priority='critical')
        ticket_id = response.json()['id']
        rejected = self.api.post('/tickets/' + ticket_id + '/transitions', headers=headers('admin'), json={'action': 'reject', 'reason': 'Synthetic duplicate issue'})
        self.assertEqual(rejected.status_code, 200)
        summary = self.api.get('/dashboard/summary', headers=headers('reporter')).json()
        self.assertEqual(summary['urgent'], 1)
        with self.lab.session() as session:
            expected = session.scalar(select(func.count()).select_from(MaintenanceTicket).where(
                MaintenanceTicket.reported_by_id == self.ids['reporter'],
                MaintenanceTicket.status.not_in(('closed', 'rejected'))))
        self.assertEqual(summary['active'], expected)

    def test_report_detail_comment_and_admin_assignment_flow(self):
        response = report(self.api, self.ids)
        self.assertEqual(response.status_code, 201)
        ticket_id = response.json()['id']
        ticket = self.api.get('/tickets/' + ticket_id, headers=headers('reporter')).json()
        self.assertEqual(ticket['description'], 'Synthetic issue')
        self.assertEqual(self.api.get('/tickets/' + ticket_id, headers=headers('other')).status_code, 404)
        self.assertEqual(self.api.post('/tickets/' + ticket_id + '/comments', headers=headers('reporter'), json={'body': 'Helpful update'}).status_code, 201)
        self.assertEqual(self.api.post('/tickets/' + ticket_id + '/transitions', headers=headers('admin'), json={'action': 'assign', 'technician_id': str(self.ids['tech'])}).status_code, 200)
        self.assertGreaterEqual(self.api.get('/dashboard/summary', headers=headers('tech')).json()['active'], 1)
        self.assertEqual(self.api.post('/tickets/' + ticket_id + '/transitions', headers=headers('reporter'), json={'action': 'reject', 'reason': 'No access'}).status_code, 403)


if __name__ == '__main__':
    unittest.main(verbosity=2)
