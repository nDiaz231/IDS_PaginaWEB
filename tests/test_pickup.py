import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from biblioteca import create_app, data, db, circulation
from biblioteca.errors import DomainError
from biblioteca.timeutils import pickup_deadline, pickup_expired, local_input


class PickupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.now = datetime(2026, 11, 11, 12, tzinfo=timezone.utc)
        self.app = create_app({'TESTING': True, 'APP_MODE': 'local',
            'SECRET_KEY': 'test-only-' * 8, 'DATABASE': str(Path(self.tmp.name) / 'test.sqlite3'),
            'CLOCK': lambda: self.now, 'WTF_CSRF_ENABLED': False})
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.initialize()
        with db.transaction():
            self.admin = data.add_user('admin@test.test', 'Admin', 'unused', role='admin')
            self.student = data.add_user('student@test.test', 'Student', 'unused')
            self.book = data.add_book(dict(title='Prueba', author='Autor', category='Libros',
                isbn='', publication_year=2026, description=''))
            self.copy = data.add_copy(self.book, 'TEST-1', 'general', 'Mostrador')
        self.req = circulation.submit(self.student, self.book, 'general', 3)
        circulation.approve(self.admin, self.req, self.copy)

    def tearDown(self):
        self.ctx.pop()
        self.tmp.cleanup()

    def ready(self):
        circulation.mark_ready(self.admin, self.req)

    def test_preparation_does_not_expire(self):
        self.now += timedelta(days=3)
        circulation.expire_pickups()
        self.assertEqual(data.copy(self.copy)['state'], 'asignado')
        self.assertIsNone(pickup_deadline(data.request(self.req)))

    def test_exact_boundary_and_single_audit(self):
        self.ready()
        self.now += timedelta(hours=24, seconds=-1)
        circulation.expire_pickups()
        self.assertEqual(data.request(self.req)['status'], 'aprobada')
        self.now += timedelta(seconds=1)
        circulation.expire_pickups()
        circulation.expire_pickups()
        self.assertTrue(pickup_expired(data.request(self.req)))
        self.assertEqual(data.copy(self.copy)['state'], 'disponible')
        self.assertEqual(len([e for e in data.audit_log() if e['event']=='reserva_vencida']), 1)

    def test_repeated_ready_cannot_extend_deadline(self):
        self.ready()
        deadline = pickup_deadline(data.request(self.req))
        self.now += timedelta(hours=1)
        with self.assertRaises(DomainError):
            self.ready()
        self.assertEqual(pickup_deadline(data.request(self.req)), deadline)

    def test_expired_delivery_rejected_and_release_persists(self):
        self.ready()
        self.now += timedelta(hours=24)
        with self.assertRaises(DomainError):
            circulation.deliver(self.admin, self.req, local_input(self.now + timedelta(days=3)), True)
        self.assertEqual(data.copy(self.copy)['state'], 'disponible')
        self.assertEqual(data.loans(), [])

    def test_delivered_loan_does_not_expire(self):
        self.ready()
        circulation.deliver(self.admin, self.req, local_input(self.now + timedelta(days=3)), True)
        self.now += timedelta(hours=25)
        circulation.expire_pickups()
        self.assertEqual(data.request(self.req)['status'], 'atendida')
        self.assertEqual(data.copy(self.copy)['state'], 'prestado')

    def test_release_notifies_watchers(self):
        with db.transaction():
            data.set_watch(self.student, self.book, True)
        self.ready()
        self.now += timedelta(hours=24)
        circulation.expire_pickups()
        self.assertEqual(len(data.notifications(self.student)), 1)

    def test_pages_show_deadline_and_expiry(self):
        self.ready()
        client = self.app.test_client()
        with client.session_transaction() as session:
            session['user_id'] = self.student
            session['session_version'] = data.user(self.student)['session_version']
        response = client.get(f'/solicitudes/{self.req}')
        self.assertEqual(response.status_code, 200)
        self.assertIn('Retirar antes de', response.text)
        self.now += timedelta(hours=24)
        response = client.get(f'/solicitudes/{self.req}')
        self.assertIn('Reserva vencida', response.text)
        self.assertNotIn('Cancelar solicitud</h2>', response.text)


if __name__ == '__main__':
    unittest.main()
