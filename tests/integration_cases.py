"""Real PostgreSQL acceptance cases; invoked inside an isolated lab fixture."""
import unittest
from decimal import Decimal
from uuid import uuid4
import psycopg
from sqlalchemy import select,text,func
from sqlalchemy.exc import IntegrityError
from college_maintenance.models import Asset,MaintenanceTicket,WorkOrder,WorkOrderPart,SparePart
from college_maintenance.reports import costs_by_department_query
from college_maintenance.reads import scope_for_actor
from labs.shared.workflow_lab import client,headers,report

def suite(lab,ids):
    class PostgreSQLIntegration(unittest.TestCase):
        def test_check_constraint_bypassing_orm(self):
            with self.assertRaises(IntegrityError) as error:
                with lab.engine.begin() as c:c.execute(text(f"INSERT INTO {lab.schema}.assets(asset_code,name,department_id,category_id,status) VALUES ('INVALID','Bad',:d,:c,'invalid')"),dict(d=ids['dept'],c=ids['category']))
            self.assertEqual(error.exception.orig.sqlstate,'23514')

        def test_http_actor_scope(self):
            with client(lab,ids) as api:
                response=report(api,ids);self.assertEqual(response.status_code,201)
                key=response.json()['id']
                self.assertEqual(api.get('/tickets/'+key,headers=headers('other_admin')).status_code,404)
                self.assertEqual(api.get('/tickets/'+key,headers=headers('reporter')).status_code,200)

        def test_report_permission(self):
            with client(lab,ids) as api:self.assertEqual(api.get('/reports/costs',headers=headers('reporter')).status_code,403)

        def test_authentication_required(self):
            with client(lab,ids) as api:self.assertEqual(api.get('/tickets').status_code,401)

        def test_real_commit_and_rollback(self):
            try:
                with lab.session() as s,s.begin():
                    s.add(Asset(asset_code='ROLLBACK-59',name='Never committed',department_id=ids['dept'],category_id=ids['category']));s.flush();raise RuntimeError('injected')
            except RuntimeError:pass
            self.assertEqual(lab.driver().execute(f"SELECT count(*) FROM {lab.schema}.assets WHERE asset_code='ROLLBACK-59'").fetchone()[0],0)

        def test_distinct_backend_lock_conflict(self):
            first=lab.driver();second=lab.driver()
            self.assertNotEqual(first.info.backend_pid,second.info.backend_pid)
            second.execute("SET lock_timeout='150ms'")
            with first.transaction():
                first.execute(f'SELECT id FROM {lab.schema}.assets WHERE id=%s FOR UPDATE',(ids['asset'],))
                with self.assertRaises(psycopg.errors.LockNotAvailable):second.execute(f'UPDATE {lab.schema}.assets SET location=location WHERE id=%s',(ids['asset'],))

        def test_empty_department_report(self):
            with lab.session() as s:
                rows=s.execute(costs_by_department_query(scope_for_actor(s,ids['other_admin']))).all()
                self.assertEqual(len(rows),1);self.assertEqual(rows[0].total_cost,Decimal('0'))

        def test_metadata_and_actual_foreign_keys(self):
            with lab.engine.connect() as c:
                self.assertGreater(c.scalar(text("SELECT count(*) FROM pg_constraint WHERE connamespace=to_regnamespace(:s) AND contype='f'"),{'s':lab.schema}),10)
    return unittest.defaultTestLoader.loadTestsFromTestCase(PostgreSQLIntegration)
