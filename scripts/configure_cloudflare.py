"""GitHub Actions configura identificadores públicos; nunca escribe secretos al repo."""
import json
import os
from pathlib import Path
import re
from uuid import UUID

path = Path('wrangler.jsonc')
config = json.loads(path.read_text())
database = os.environ.get('CLOUDFLARE_D1_ID', '').strip()
host = os.environ.get('SITE_HOST', '').strip().lower()
try:
    valid_database = UUID(database).int != 0 and str(UUID(database)) == database.lower()
except ValueError:
    valid_database = False
if not valid_database:
    raise SystemExit('Configura CLOUDFLARE_D1_ID con el UUID de tu base D1.')
if not re.fullmatch(r'[a-z0-9.-]+\.workers\.dev', host):
    raise SystemExit('SITE_HOST debe ser biblioteca-mejorada.TU-SUBDOMINIO.workers.dev, sin https:// ni rutas.')
config['d1_databases'][0]['database_id'] = database
config['vars']['SITE_HOST'] = host
path.write_text(json.dumps(config, indent=2)+'\n')
