from datetime import timedelta
import sqlite3
from pathlib import Path
import unittest
import test_pickup
from biblioteca import data, db, circulation, rules
from biblioteca.errors import DomainError
from biblioteca.timeutils import local_input


class DurationTests(unittest.TestCase):
    setUp = test_pickup.PickupTests.setUp
    tearDown = test_pickup.PickupTests.tearDown
    ready = test_pickup.PickupTests.ready
    def test_limits(self):
        for collection, maximum in [('alta_demanda', 14), ('general', 30)]:
            for days in [1, maximum]:
                self.assertEqual(rules.validate_requested_days(str(days), collection), days)
            for days in ['', None, '1.5', 'abc', 0, -1, maximum + 1, True]:
                with self.subTest(collection=collection, days=days):
                    with self.assertRaises(DomainError):
                        rules.validate_requested_days(days, collection)

    def test_duration_is_saved(self):
        circulation.cancel(self.student, self.req)
        ident = circulation.submit(self.student, self.book, 'general', '30')
        self.assertEqual(data.request(ident)['requested_days'], 30)

    def test_missing_or_tampered_duration_rejected_by_http(self):
        circulation.cancel(self.student, self.req)
        client = self.app.test_client()
        with client.session_transaction() as session:
            session['user_id'] = self.student
            session['session_version'] = data.user(self.student)['session_version']
        for days in ['', '31', '1.5']:
            response = client.post(f'/libros/{self.book}/solicitar', data={'collection_id':'general', 'requested_days':days})
            self.assertEqual(response.status_code, 400)
        self.assertFalse(data.has_open_title(self.student, self.book))

    def test_high_demand_validates_before_creating_request(self):
        with db.transaction():
            data.add_copy(self.book, 'HIGH-1', 'alta_demanda', 'Mostrador')
        circulation.cancel(self.student, self.req)
        with self.assertRaises(DomainError):
            circulation.submit(self.student, self.book, 'alta_demanda', 15)
        ident = circulation.submit(self.student, self.book, 'alta_demanda', 14)
        self.assertEqual(data.request(ident)['requested_days'], 14)

    def test_waiting_does_not_consume_loan_days(self):
        self.now += timedelta(days=5)
        self.ready()
        self.now += timedelta(hours=12)
        row = data.request(self.req)
        due = rules.suggested_due(self.student, 'general', row['requested_days'])
        self.assertEqual(due, self.now + timedelta(days=3))
        ident = circulation.deliver(self.admin, self.req, local_input(due), True)
        self.assertEqual(data.loan(ident)['due_at'], '2026-11-20T00:00:00Z')

    def test_admin_cannot_exceed_requested_days(self):
        self.ready()
        with self.assertRaises(DomainError):
            circulation.deliver(self.admin, self.req, local_input(self.now + timedelta(days=4)), True)
        self.assertEqual(data.loans(), [])

    def test_month_boundary_is_thirty_days(self):
        self.now = self.now.replace(month=1, day=31)
        self.assertEqual((rules.suggested_due(self.student, 'general', 30) - self.now).days, 30)

    def test_upgrade_preserves_existing_requests_and_backups(self):
        db.close_db()
        legacy = Path(self.tmp.name) / 'legacy.sqlite3'
        self.app.config['DATABASE'] = str(legacy)
        source = Path(db.__file__).parent
        conn = sqlite3.connect(legacy)
        conn.executescript((source / 'schema.sql').read_text(encoding='utf-8'))
        conn.executescript((source / 'migrations/002_favorites_security.sql').read_text(encoding='utf-8'))
        conn.execute("INSERT INTO users(email,name,password_hash,role,user_type) VALUES('old@test.test','Old','unused','alumno','pregrado')")
        conn.execute("INSERT INTO books(title,author,category) VALUES('Old book','Author','Test')")
        conn.execute("INSERT INTO requests(user_id,book_id,collection_id,created_at) VALUES(1,1,'general','2026-11-01T00:00:00Z')")
        conn.commit()
        conn.close()
        backup = db.upgrade()
        self.assertTrue(backup.exists())
        self.assertEqual(data.metadata('schema_version'), '5')
        self.assertIsNone(data.request(1)['requested_days'])
        self.assertEqual(data.request(1)['title'], 'Old book')
        self.assertIsNone(db.upgrade())
