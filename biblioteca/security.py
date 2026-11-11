import hashlib
import hmac
from datetime import timedelta
from flask import current_app, request
from . import data
from .db import transaction
from .timeutils import now_utc, stamp


def login_key(value):
    secret = current_app.config['SECRET_KEY'].encode()
    return hmac.new(secret, value.encode(), hashlib.sha256).hexdigest()


def reserve_login_attempt(email):
    # No confiamos en X-Forwarded-For enviado por el visitante.
    client_key = login_key(request.remote_addr or 'unknown')
    account_key = login_key(email)
    since = stamp(now_utc() - timedelta(minutes=15))
    with transaction():
        counts = data.login_counts(account_key, client_key, since)
        if counts['account'] >= 5 or counts['client'] >= 50:
            return None
        data.add_login_attempt(account_key, client_key)
    return account_key


def valid_password(password):
    return 12 <= len(password) <= 200 and password != 'DemoUCN2026!'


def reserve_registration_attempt():
    # Límites persistentes, compartidos entre procesos. No se guardan IP, RUT ni correo.
    client_key = login_key('registration:' + (request.remote_addr or 'unknown'))
    day = stamp(now_utc() - timedelta(days=1))
    window = stamp(now_utc() - timedelta(minutes=15))
    with transaction():
        data.write('DELETE FROM registration_attempts WHERE attempted_at<?', (day,))
        counts = data.one('''SELECT count(*) AS day_total,
            COALESCE(sum(attempted_at>=?),0) AS window_total,
            COALESCE(sum(client_key=?),0) AS client_day,
            COALESCE(sum(client_key=? AND attempted_at>=?),0) AS client_window
            FROM registration_attempts''', (window,client_key,client_key,window))
        if (counts['client_window'] >= 5 or counts['client_day'] >= 30
                or counts['window_total'] >= 50 or counts['day_total'] >= 500):
            return False
        data.write('INSERT INTO registration_attempts(client_key,attempted_at) VALUES(?,?)', (client_key,stamp()))
    return True


def deployment_problems():
    counts = data.deployment_counts()
    problems = []
    if counts['demo_active']:
        problems.append('Desactiva las cuentas demo con disable-demo-accounts.')
    if not counts['admins']:
        problems.append('Crea una cuenta de administrador propia con create-user.')
    return problems
