## Tecnologías

- **Backend:** Python 3.12 o superior y Flask.
- **Interfaz:** plantillas Jinja, HTML, CSS y JavaScript.
- **Persistencia local:** SQLite.
- **Despliegue:** Cloudflare Workers y D1.
- **Herramientas:** uv para las dependencias de Python y npm para las herramientas de despliegue.
- **Automatización:** GitHub Actions con un workflow de publicación manual.

Las dependencias y sus versiones se definen en [pyproject.toml](pyproject.toml), [uv.lock](uv.lock), [package.json](package.json) y [package-lock.json](package-lock.json).

Ejecución local
1. Requisitos
Instala Git, Python 3.12 o superior y uv antes de comenzar.

2. Obtener el proyecto e instalar dependencias

bash
git clone https://github.com/nDiaz231/IDS_PaginaWEB.git
cd IDS_PaginaWEB
uv sync --locked


3. Configurar el entorno

Genera una clave aleatoria:
bash
uv run python -c "import secrets; print(secrets.token_hex(32))"
Crea un archivo `.env` en la raíz del proyecto y reemplaza el valor de `SECRET_KEY` por la clave generada:
dotenv
APP_MODE=local
SECRET_KEY=REEMPLAZAR_POR_LA_CLAVE_GENERADA
DATABASE_PATH=instance/biblioteca.sqlite3
COOKIE_SECURE=0
TRUSTED_HOSTS=localhost,127.0.0.1
DUE_SOON_HOURS=48


La aplicación exige una clave de al menos 32 caracteres y rechaza valores que comiencen con `REEMPLAZAR`. Mantén `.env`, las bases de datos locales y sus respaldos fuera del control de versiones.

4. Inicializar una base de datos nueva

bash
uv run flask --app app init-db


Este comando crea el esquema sin cuentas ni datos de ejemplo y no sobrescribe una base existente.

Para explorar el proyecto con datos de demostración, ejecuta lo siguiente sobre la base vacía:

bash
uv run flask --app app seed-demo


El comando muestra las credenciales de demostración en la terminal. Estas cuentas son exclusivamente para uso local.

Como alternativa, crea una cuenta propia; el comando solicita la contraseña de forma interactiva:

bash
uv run flask --app app create-user --email tu-correo@ucn.cl --name "Tu nombre" --role admin


5. Iniciar la aplicación

bash
uv run flask --app app run

Abre [http://127.0.0.1:5000](http://127.0.0.1:5000). El servidor de desarrollo se utiliza para la ejecución local.

## Estructura del repositorio

.
├── app.py                  # Punto de entrada de Flask
├── biblioteca/             # Aplicación, lógica de negocio y acceso a datos
│   ├── migrations/         # Migraciones de la base local
│   ├── static/             # Estilos, JavaScript e imágenes
│   └── templates/          # Plantillas de la interfaz
├── cloudflare/migrations/  # Migraciones para D1
├── scripts/                # Configuración y empaquetado para Cloudflare
├── src/worker.py           # Punto de entrada del Worker
├── .github/workflows/      # Automatización de publicación
├── pyproject.toml          # Dependencias de Python
└── wrangler.jsonc          # Configuración de Cloudflare

Publicación

El workflow [Publicar Biblioteca en Cloudflare](.github/workflows/publicar.yml) se ejecuta manualmente desde GitHub Actions.

Utiliza los secretos `CLOUDFLARE_ACCOUNT_ID` y `CLOUDFLARE_API_TOKEN`, junto con las variables `CLOUDFLARE_D1_ID` y `SITE_HOST`. Instala las herramientas, prepara el paquete, comprueba el despliegue, aplica las migraciones remotas pendientes y publica la aplicación.

Antes de ejecutarlo, revisa la configuración de [wrangler.jsonc](wrangler.jsonc) y los scripts de [scripts/](scripts/). La publicación modifica el entorno remoto y su base de datos.

## Criterios para contribuir

1. Describe el problema o la mejora en un issue, incluyendo el resultado esperado.
2. Trabaja en una rama con un nombre descriptivo.
3. Mantén cada cambio centrado en un objetivo y evita incluir credenciales o datos personales.
4. Verifica los flujos afectados para los roles correspondientes y documenta las pruebas realizadas.
5. Abre un pull request con el contexto, los cambios y los pasos de validación.

Para las mejoras de interfaz, considera navegación por teclado, etiquetas claras, contraste y mensajes comprensibles. Estos son criterios de trabajo; no constituyen una certificación de accesibilidad.

## Evaluación del proyecto

Para comprobar el aporte de BiblioUCN, se propone medir el tiempo necesario para consultar disponibilidad y completar una solicitud, la tasa de tareas completadas y las dificultades de uso detectadas en pruebas con usuarios.

## Licencia

Actualmente, el repositorio no incluye un archivo de licencia. Las condiciones de reutilización y distribución deberán ser definidas por sus responsables.
