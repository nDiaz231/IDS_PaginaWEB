"""Registro público: validación estricta y cuentas pendientes de revisión humana."""
import re
import sqlite3
import unicodedata
from flask import Blueprint, g, redirect, render_template, request, url_for
from . import data
from .db import transaction
from .errors import DomainError
from .passwords import generate_password_hash
from .security import reserve_registration_attempt
from .timeutils import now_utc, SANTIAGO

bp = Blueprint('registration', __name__)
ALLOWED_DOMAINS = frozenset(('alumnos.ucn.cl', 'ce.ucn.cl'))
PASSWORD_HELP = 'Usa entre 8 y 200 caracteres, al menos una mayúscula y un carácter especial (por ejemplo !, @ o #).'


def institutional_email(value):
    email = value.strip().lower()
    local, separator, domain = email.rpartition('@')
    if (not separator or domain not in ALLOWED_DOMAINS or len(local) > 64
            or not re.fullmatch(r"[a-z0-9_%+\-]+(?:\.[a-z0-9_%+\-]+)*", local)):
        raise DomainError('Solo se permiten correos @alumnos.ucn.cl o @ce.ucn.cl.', 400)
    return email


def normalize_rut(value):
    if len(value) > 16 or not re.fullmatch(r'(?:[1-9][0-9]{6,7}-?[0-9kK]|[1-9][0-9]?\.[0-9]{3}\.[0-9]{3}-[0-9kK])', value.strip()):
        raise DomainError('Ingresa un RUT válido, con su dígito verificador.', 400)
    compact = value.strip().replace('.', '').replace('-', '').upper()
    if not re.fullmatch(r'[0-9]{7,8}[0-9K]', compact) or compact[0] == '0':
        raise DomainError('Ingresa un RUT válido, con su dígito verificador.', 400)
    body, check = compact[:-1], compact[-1]
    total = sum(int(digit) * (2 + index % 6) for index, digit in enumerate(reversed(body)))
    remainder = 11 - total % 11
    expected = '0' if remainder == 11 else 'K' if remainder == 10 else str(remainder)
    if check != expected or len(set(body)) == 1:
        raise DomainError('El dígito verificador del RUT no es válido.', 400)
    return f'{body}-{check}'


def registration_password(password):
    return (8 <= len(password) <= 200 and any(c.isupper() for c in password)
            and any(unicodedata.category(c)[0] in 'PS' for c in password)
            and not any(unicodedata.category(c)[0] == 'C' for c in password)
            and password != 'DemoUCN2026!')


def student_fields(form):
    # Solo se extraen campos explícitos: nunca se aceptan rol ni habilitaciones.
    email = institutional_email(form.get('email', ''))
    name = unicodedata.normalize('NFC', ' '.join(form.get('name', '').split()))
    if (not 5 <= len(name) <= 120 or len(name.split()) < 2 or not all(any(c.isalpha() for c in word) for word in name.split())
            or not all(c.isalpha() or c in " '-’" or unicodedata.category(c) == 'Mn' for c in name)):
        raise DomainError('Ingresa tu nombre completo y apellidos, entre 5 y 120 caracteres.', 400)
    rut = normalize_rut(form.get('rut', ''))
    year = form.get('admission_year', '')
    current_year = now_utc().astimezone(SANTIAGO).year
    if not re.fullmatch(r'[0-9]{4}', year) or not 1900 <= int(year) <= current_year:
        raise DomainError(f'El año de ingreso debe estar entre 1900 y {current_year}.', 400)
    career = unicodedata.normalize('NFC', ' '.join(form.get('career', '').split()))
    if (not 3 <= len(career) <= 120 or not any(c.isalpha() for c in career)
            or not all(c.isalnum() or c in " '-’.,/()&" or unicodedata.category(c) == 'Mn' for c in career)):
        raise DomainError('Ingresa una carrera válida, entre 3 y 120 caracteres.', 400)
    password = form.get('password', '')
    if not registration_password(password):
        raise DomainError(PASSWORD_HELP, 400)
    if password != form.get('password_confirm', ''):
        raise DomainError('Las contraseñas no coinciden.', 400)
    return dict(email=email, name=name, rut=rut, admission_year=int(year), career=career), password


@bp.route('/crear-cuenta', methods=['GET', 'POST'])
def register():
    if g.user:
        return redirect(url_for('views.home'))
    error = None
    if request.method == 'POST':
        if not reserve_registration_attempt():
            return render_template('register.html', error='El registro está temporalmente limitado por demasiados intentos. Inténtalo más tarde.', current_year=now_utc().astimezone(SANTIAGO).year), 429, {'Retry-After': '900'}
        try:
            if request.files or any(len(request.form.getlist(key)) != 1 for key in request.form):
                raise DomainError('El formulario contiene campos repetidos o archivos no permitidos.', 400)
            fields, password = student_fields(request.form)
            password_hash = generate_password_hash(password)
            try:
                with transaction():
                    # Misma respuesta para duplicados: no revela si existe un correo o RUT.
                    if not data.user_by_email(fields['email']) and not data.profile_by_rut(fields['rut']):
                        ident = data.add_user(fields['email'], fields['name'], password_hash, enabled=False,
                                              reason='Registro pendiente de validación por administración.')
                        data.write('UPDATE users SET account_active=0 WHERE id=?', (ident,))
                        data.add_student_profile(ident, fields)
                        data.audit(None, 'registro_alumno_pendiente', ident)
            except sqlite3.IntegrityError:
                # Dos registros simultáneos tampoco revelan la existencia de cuentas.
                if not data.user_by_email(fields['email']) and not data.profile_by_rut(fields['rut']):
                    raise
            return redirect(url_for('registration.received'), code=303)
        except DomainError as exc:
            error = exc.message
    return render_template('register.html', error=error, current_year=now_utc().astimezone(SANTIAGO).year), 400 if error else 200


@bp.get('/registro-recibido')
def received():
    return render_template('registration_received.html')
