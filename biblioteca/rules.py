"""Política de circulación; no conoce HTTP ni un formato institucional futuro."""
from datetime import timedelta
from . import data
from .errors import DomainError
from .timeutils import now_utc, SANTIAGO


def eligible(user_id):
    user = data.user(user_id)
    if not user or user['role'] != 'alumno':
        raise DomainError('El solicitante debe ser un alumno.', 400)
    if not user['account_active'] or not user['lending_enabled']:
        raise DomainError('Cuenta no habilitada para préstamos. ' + (user['block_reason'] or 'Consulta con biblioteca.'))
    if data.has_overdue(user_id):
        raise DomainError('Hay material vencido pendiente de devolución. Regulariza la situación con biblioteca.')
    return user


def capacity(user_id, collection_id, exclude_request=0):
    user = eligible(user_id)
    policy = data.rule(user['user_type'], collection_id)
    if not policy:
        raise DomainError('No existe una regla de préstamo para este tipo de usuario y colección.')
    if data.commitments(user_id, collection_id, exclude_request) >= policy['max_items']:
        raise DomainError(f"Se alcanzó el límite de {policy['max_items']} ejemplares de esta colección, incluyendo asignaciones para retiro.")
    return policy


def maximum_days(collection_id):
    if collection_id not in ('alta_demanda', 'general'):
        raise DomainError('Selecciona una colección válida.', 400)
    return 14 if collection_id == 'alta_demanda' else 30


def validate_requested_days(value, collection_id):
    maximum = maximum_days(collection_id)
    if not isinstance(value, (str, int)) or isinstance(value, bool) or not str(value).isascii() or not str(value).isdigit():
        raise DomainError(f'Indica una duración entera entre 1 y {maximum} días.', 400)
    days = int(value)
    if not 1 <= days <= maximum:
        raise DomainError(f'Esta colección permite entre 1 y {maximum} días de préstamo.', 400)
    return days


def suggested_due(user_id, collection_id, requested_days=None):
    user = data.user(user_id)
    policy = data.rule(user['user_type'], collection_id)
    if not policy:
        return None
    days = requested_days if requested_days is not None else min(policy['loan_days'], maximum_days(collection_id))
    days = validate_requested_days(days, collection_id)
    return (now_utc() + timedelta(days=days)).replace(second=0, microsecond=0)
