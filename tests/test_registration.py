import re
import sqlite3
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch
from werkzeug.datastructures import MultiDict
import test_pickup
from biblioteca import data, db
from biblioteca.passwords import check_password_hash, _derive, _tag
from biblioteca.registration import institutional_email, normalize_rut, registration_password
from biblioteca.errors import DomainError


class RegistrationTests(unittest.TestCase):
    setUp = test_pickup.PickupTests.setUp
    tearDown = test_pickup.PickupTests.tearDown

    def form(self, **changes):
        fields = dict(name='Registro Prueba Demo', email='registro.prueba@alumnos.ucn.cl',
                      rut='12.345.678-5', admission_year='2024', career='Ingeniería Civil',
                      password='Prueba1!', password_confirm='Prueba1!')
        fields.update(changes)
        return fields

    def client_for(self, user):
        client = self.app.test_client()
        with client.session_transaction() as session:
            session['user_id'] = user
            session['session_version'] = data.user(user)['session_version']
        return client

    def test_domains_exact_and_password_requirements(self):
        for email in [' Alumno@ALUMNOS.UCN.CL ', 'nombre@ce.ucn.cl']:
            self.assertIn(institutional_email(email).split('@')[1], ('alumnos.ucn.cl','ce.ucn.cl'))
        for email in ['a@ucn.cl','a@gmail.com','a@alumnos.ucn.cl.evil.org','a@evilalumnos.ucn.cl',
                      'a@ce.ucn.cl@evil.org','a@sub.ce.ucn.cl','a..b@ce.ucn.cl','a@ce.ucn.cl\nBcc: x@x.cl']:
            with self.subTest(email=email), self.assertRaises(DomainError):
                institutional_email(email)
        self.assertTrue(registration_password('Prueba1!'))
        for password in ['Ab1!', 'minuscula!', 'SinSimbolo1', 'A'*201+'!', 'Abcdef\n!', 'DemoUCN2026!']:
            self.assertFalse(registration_password(password))

    def test_rut_normalization_and_checksum(self):
        self.assertEqual(normalize_rut('12.345.678-5'), '12345678-5')
        self.assertEqual(normalize_rut('123456785'), '12345678-5')
        for rut in ['12.345.678-9', '00000000-0', '12-34-5678-5', '12345678', '11111111-1']:
            with self.subTest(rut=rut), self.assertRaises(DomainError):
                normalize_rut(rut)

    def test_register_persists_private_pending_profile_and_cannot_escalate(self):
        client = self.app.test_client()
        response = client.post('/crear-cuenta',data=self.form(role='admin',account_active='1',lending_enabled='1'))
        self.assertEqual(response.status_code,303)
        user = data.user_by_email(self.form()['email'])
        self.assertEqual(user['role'],'alumno')
        self.assertEqual(user['account_active'],0)
        self.assertEqual(user['lending_enabled'],0)
        self.assertNotEqual(user['password_hash'],'Prueba1!')
        self.assertTrue(check_password_hash(user['password_hash'],'Prueba1!'))
        db.close_db()
        profile=data.student_profile(user['id'])
        self.assertEqual(profile['rut'],'12345678-5')
        self.assertEqual(profile['career'],'Ingeniería Civil')
        self.assertEqual(profile['admission_year'],2024)
        self.assertIsNone(profile['reviewed_at'])
        response=client.post('/ingresar',data={'email':user['email'],'password':'Prueba1!'})
        self.assertEqual(response.status_code,400)
        self.assertEqual(client.get('/admin/alumnos').status_code,302)
        with client.session_transaction() as session:
            self.assertNotIn('user_id',session)
        self.assertNotIn('12345678', str(data.audit_log()))

    def test_duplicate_response_same_and_no_overwrite(self):
        client=self.app.test_client()
        first=client.post('/crear-cuenta',data=self.form())
        user=data.user_by_email(self.form()['email'])
        for fields in [self.form(name='Nombre Diferente'),self.form(email='otra@ce.ucn.cl')]:
            response=client.post('/crear-cuenta',data=fields)
            self.assertEqual((response.status_code,response.location),(first.status_code,first.location))
        self.assertEqual(data.user(user['id'])['name'],self.form()['name'])
        self.assertIsNone(data.user_by_email('otra@ce.ucn.cl'))

    def test_invalid_inputs_rejected_and_password_not_echoed(self):
        client=self.app.test_client()
        cases=[self.form(admission_year='2099'),self.form(career='<script>alert(1)</script>'),
               self.form(password_confirm='distinta'),self.form(name="Robert'); DROP TABLE users;--"),
               self.form(rut='12.345.678-9')]
        for fields in cases:
            response=client.post('/crear-cuenta',data=fields)
            self.assertEqual(response.status_code,400)
            self.assertNotIn('value="Prueba1!"', response.text)
            self.assertNotIn('<script>alert(1)</script>', response.text)
        self.assertIsNone(data.user_by_email(self.form()['email']))
        self.assertIsNotNone(data.user(self.admin))

    def test_rate_limit_before_password_hash_and_spoofed_ip_ignored(self):
        client=self.app.test_client()
        for _ in range(5):
            self.assertEqual(client.post('/crear-cuenta',data=self.form(email='bad@evil.org')).status_code,400)
        with patch('biblioteca.registration.generate_password_hash') as expensive:
            response=client.post('/crear-cuenta',data=self.form(),headers={'X-Forwarded-For':'8.8.8.8','CF-Connecting-IP':'9.9.9.9'})
            self.assertEqual(response.status_code,429)
            self.assertEqual(response.headers['Retry-After'],'900')
            expensive.assert_not_called()
        self.now+=timedelta(minutes=16)
        self.assertEqual(client.post('/crear-cuenta',data=self.form()).status_code,303)

    def test_csrf_size_and_duplicate_fields(self):
        self.app.config['WTF_CSRF_ENABLED']=True
        client=self.app.test_client()
        self.assertEqual(client.post('/crear-cuenta',data=self.form()).status_code,400)
        page=client.get('/crear-cuenta')
        token=re.search(r'name="csrf_token" value="([^"]+)"',page.text).group(1)
        fields=self.form();fields['csrf_token']=token
        self.assertEqual(client.post('/crear-cuenta',data=fields).status_code,303)
        self.assertEqual(client.post('/crear-cuenta',data='x'*(65*1024),content_type='application/x-www-form-urlencoded').status_code,413)
        self.app.config['WTF_CSRF_ENABLED']=False
        duplicate=MultiDict(list(self.form().items())+[('email','attacker@ce.ucn.cl')])
        self.assertEqual(client.post('/crear-cuenta',data=duplicate).status_code,400)

    def test_review_admin_only_explicit_and_no_activation_bypass(self):
        client=self.app.test_client()
        client.post('/crear-cuenta',data=self.form())
        user=data.user_by_email(self.form()['email'])
        url=f"/admin/cuentas/{user['id']}/registro"
        self.assertEqual(client.get(url).status_code,302)
        student=self.client_for(self.student)
        self.assertEqual(student.get(url).status_code,403)
        self.assertEqual(student.post(url,data={'verified':'yes'}).status_code,403)
        admin=self.client_for(self.admin)
        self.assertIn('12345678-5',admin.get(url).text)
        self.assertIn('Revisar registro',admin.get('/admin/alumnos').text)
        self.assertEqual(admin.post(url,data={}).status_code,400)
        self.assertEqual(admin.post(f"/admin/alumnos/{user['id']}/habilitacion",data={'account_active':'yes','lending_enabled':'yes'}).status_code,400)
        self.assertEqual(admin.post(f"/admin/cuentas/{user['id']}/clave",data={'password':'NuevaClaveDemo!'}).status_code,400)
        # Incluso una activación manual accidental no elimina la revisión pendiente.
        with db.transaction():
            data.write('UPDATE users SET account_active=1 WHERE id=?',(user['id'],))
        self.assertEqual(client.post('/ingresar',data={'email':user['email'],'password':'Prueba1!'}).status_code,400)
        result=admin.post(url,data={'verified':'yes'})
        self.assertEqual(result.status_code,302)
        self.assertEqual(admin.post(url,data={'verified':'yes'}).status_code,409)
        login=client.post('/ingresar',data={'email':user['email'],'password':'Prueba1!'})
        self.assertEqual(login.status_code,302)
        self.assertEqual(data.user(user['id'])['lending_enabled'],1)
        self.assertEqual(client.get('/').status_code,200)
        self.assertIn('registro_alumno_validado',[r['event'] for r in data.audit_log()])

    def test_html_headers_and_no_profile_leaks(self):
        client=self.app.test_client()
        for url in ['/crear-cuenta','/ingresar','/registro-recibido']:
            response=client.get(url)
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.headers['Cache-Control'],'no-store')
            self.assertEqual(response.headers['X-Frame-Options'],'DENY')
        self.assertIn('Crear cuenta',client.get('/ingresar').text)
        self.assertNotIn('12345678-5',client.get('/registro-recibido').text)

    def test_cloud_migration_creates_matching_schema(self):
        cloud=sqlite3.connect(':memory:')
        try:
            for file in sorted((Path(db.__file__).parent.parent/'cloudflare/migrations').glob('*.sql')):
                cloud.executescript(file.read_text(encoding='utf-8'))
            self.assertEqual(cloud.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()[0],'5')
            self.assertEqual({r[1] for r in cloud.execute('PRAGMA table_info(student_profiles)')},
                             {r[1] for r in db.get_db().execute('PRAGMA table_info(student_profiles)')})
        finally:
            cloud.close()

    def test_cloud_legacy_password_remains_valid_and_new_work_factor(self):
        from biblioteca import passwords
        salt='1'*32
        legacy=f'pbkdf2-sha256-pepper-v1:100000${salt}${_tag(_derive("ClavePrueba!",salt,100000))}'
        self.assertTrue(check_password_hash(legacy,'ClavePrueba!'))
        self.assertFalse(check_password_hash(legacy,'incorrecta'))
        self.assertEqual(passwords._CLOUD_ROUNDS,600000)

    def test_upgrade_from_current_schema_preserves_users_and_adds_profiles(self):
        db.close_db()
        legacy=Path(self.tmp.name)/'version4.sqlite3'
        self.app.config['DATABASE']=str(legacy)
        source=Path(db.__file__).parent
        conn=sqlite3.connect(legacy)
        conn.executescript((source/'schema.sql').read_text(encoding='utf-8'))
        for filename in ['002_favorites_security.sql','003_requested_days.sql','004_utilities.sql']:
            conn.executescript((source/'migrations'/filename).read_text(encoding='utf-8'))
        conn.execute("INSERT INTO users(email,name,password_hash,role,user_type) VALUES('preserved@demo.test','Preserved','unused','alumno','pregrado')")
        conn.commit()
        conn.close()
        saved=db.upgrade()
        self.assertTrue(saved.exists())
        self.assertEqual(data.user(1)['name'],'Preserved')
        self.assertEqual(data.metadata('schema_version'),'5')
        self.assertIsNone(data.student_profile(1))
        self.assertIsNone(db.upgrade())
