"""Empaqueta los recursos de Flask sin modificar las migraciones ni la base."""
from pathlib import Path
import mimetypes
import shutil

ROOT = Path(__file__).resolve().parents[1]


def prepare():
    source = ROOT / 'biblioteca'
    package = ROOT / 'python_modules'
    package.mkdir(exist_ok=True)
    target = package / 'biblioteca'
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    schema = (source / 'schema.sql').read_text(encoding='utf-8') + '\n' + (source / 'migrations/002_favorites_security.sql').read_text(encoding='utf-8')
    schema += '\n' + (source / 'migrations/003_requested_days.sql').read_text(encoding='utf-8')
    schema += '\n' + (source / 'migrations/004_utilities.sql').read_text(encoding='utf-8')
    templates = {str(p.relative_to(source / 'templates')): p.read_text(encoding='utf-8')
                 for p in sorted((source / 'templates').rglob('*.html'))}
    static = {p.name: (p.read_bytes(), mimetypes.guess_type(p.name)[0] or 'application/octet-stream')
              for p in sorted((source / 'static').iterdir()) if p.is_file()}
    (package / 'cloud_bundle.py').write_text(
        'SCHEMA = ' + repr(schema) + '\nTEMPLATES = ' + repr(templates) + '\nSTATIC = ' + repr(static) + '\n', encoding='utf-8')
    print('Aplicación empaquetada. Las migraciones existentes se conservan.')


if __name__ == '__main__':
    prepare()
