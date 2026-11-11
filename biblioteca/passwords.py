"""Hash de contraseñas local y compatible con Cloudflare Workers."""
import hashlib
import hmac
import secrets
import sys

from flask import current_app
from werkzeug import security

_CLOUD_METHOD = 'pbkdf2-sha256-pepper-v1:600000'
_CLOUD_ROUNDS = 600_000
_LEGACY_METHOD = 'pbkdf2-sha256-pepper-v1:100000'
_DUMMY_SALT = '00000000000000000000000000000000'


def _derive(password, salt, rounds=_CLOUD_ROUNDS):
    password_bytes = password.encode('utf-8')
    salt_bytes = salt.encode('utf-8')
    if sys.platform != 'emscripten':
        return hashlib.pbkdf2_hmac('sha256', password_bytes, salt_bytes, rounds)

    from js import Object, Uint8Array, crypto
    from pyodide.ffi import run_sync, to_js

    raw = Uint8Array.new(to_js(list(password_bytes)))
    salt_array = Uint8Array.new(to_js(list(salt_bytes)))
    key = run_sync(crypto.subtle.importKey('raw', raw, 'PBKDF2', False, to_js(['deriveBits'])))
    options = to_js(
        dict(name='PBKDF2', hash='SHA-256', salt=salt_array, iterations=rounds),
        dict_converter=Object.fromEntries,
    )
    bits = run_sync(crypto.subtle.deriveBits(options, key, 256))
    return bytes(Uint8Array.new(bits).to_py())


def _tag(derived):
    # La subclave para contraseñas se separa de la firma de sesiones.
    secret = current_app.config['SECRET_KEY'].encode('utf-8')
    pepper = hmac.digest(secret, b'biblioteca-mejorada/password-pepper/v1', 'sha256')
    return hmac.digest(pepper, derived, 'sha256').hex()


def generate_password_hash(password, method='pbkdf2:sha256:600000'):
    if sys.platform != 'emscripten':
        return security.generate_password_hash(password, method=method)
    salt = secrets.token_hex(16)
    return f'{_CLOUD_METHOD}${salt}${_tag(_derive(password, salt))}'


def check_password_hash(stored, password):
    method, _, rest = stored.partition('$')
    if method in (_CLOUD_METHOD, _LEGACY_METHOD):
        salt, separator, expected = rest.partition('$')
        if separator and len(salt) == 32 and len(expected) == 64:
            rounds = _CLOUD_ROUNDS if method == _CLOUD_METHOD else 100_000
            return hmac.compare_digest(_tag(_derive(password, salt, rounds)), expected)
    elif sys.platform != 'emscripten':
        return security.check_password_hash(stored, password)

    # Las cuentas desconocidas o de demostración también consumen una derivación.
    _derive(password, _DUMMY_SALT)
    return False
