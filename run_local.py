"""Demo local: base ficticia independiente y mantenimiento cada 30 segundos."""
import os
import secrets
import threading
from pathlib import Path


def main():
    from biblioteca import create_app, db
    from biblioteca.seed import seed_demo, seed_utilities_demo
    from biblioteca.circulation import expire_pickups

    os.environ['APP_MODE'] = 'local'
    os.environ['FLASK_DEBUG'] = '0'
    root = Path(__file__).resolve().parent
    instance = root / 'instance'
    instance.mkdir(exist_ok=True)
    key_file = instance / 'local-secret.txt'
    if not key_file.exists():
        key_file.write_text(secrets.token_hex(32), encoding='utf-8')
    app = create_app({
        'APP_MODE': 'local', 'SECRET_KEY': key_file.read_text(encoding='utf-8'),
        'DATABASE': str(instance / 'demo.sqlite3'),
        'SESSION_COOKIE_SECURE': False, 'TRUSTED_HOSTS': ['localhost', '127.0.0.1'],
    })
    with app.app_context():
        if not Path(app.config['DATABASE']).exists():
            db.initialize()
            seed_demo()
        else:
            db.upgrade()
        seed_utilities_demo()
        expire_pickups()

    def maintain():
        stop = threading.Event()
        while not stop.wait(30):
            try:
                with app.app_context():
                    expire_pickups()
            except Exception:
                app.logger.exception('No se pudieron liberar reservas vencidas')

    threading.Thread(target=maintain, daemon=True).start()
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
