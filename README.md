# BiblioUCN

**Una plataforma web para acercar los servicios bibliotecarios a la comunidad universitaria.**

BiblioUCN busca agilizar el acceso a los servicios de la Biblioteca de la Universidad Católica del Norte (UCN) mediante una plataforma web interactiva, orientada a la accesibilidad y a la inclusión digital. Su propósito es reducir las brechas de información y los tiempos de espera, favoreciendo la igualdad de oportunidades para la comunidad universitaria.

## Propósito e impacto social

El proyecto se alinea con el **Objetivo de Desarrollo Sostenible 10: Reducción de las desigualdades**, al proponer un acceso más claro y oportuno a la información y a los servicios bibliotecarios.

Sus objetivos son:

- **Facilitar el acceso a la información:** reunir el catálogo, la disponibilidad y el estado de las solicitudes en un mismo espacio.
- **Agilizar la atención:** permitir el seguimiento de solicitudes y préstamos desde la plataforma.
- **Promover la inclusión digital:** orientar el diseño hacia una navegación comprensible y accesible.
- **Favorecer la transparencia:** mostrar las reglas de préstamo, los vencimientos y el avance de cada solicitud.

Estos puntos expresan los objetivos del proyecto. La reducción de tiempos de espera y el cumplimiento de criterios de accesibilidad deberán evaluarse mediante pruebas y mediciones.

## Funcionalidades actuales

| Área | Funcionalidades |
| --- | --- |
| Catálogo | Búsqueda y filtros por categoría y disponibilidad; consulta de libros y ejemplares. |
| Solicitudes | Envío, consulta y cancelación de solicitudes de préstamo. |
| Préstamos | Seguimiento de préstamos y avisos de vencimiento en la plataforma. |
| Favoritos y avisos | Guardado de libros y suscripción a avisos de disponibilidad. |
| Administración | Gestión de libros, ejemplares, solicitudes, entregas y devoluciones. |
| Cuentas y trazabilidad | Roles de alumno y administrador, habilitación de usuarios y registro de actividad. |

> Enviar una solicitud no garantiza la asignación de un ejemplar: requiere revisión por parte de la administración.

## Requisitos acordados para la próxima versión

Estos requisitos describen el comportamiento objetivo; su inclusión aquí no implica que ya estén implementados.

- **Catálogo unificado:** libros, juegos de mesa y materiales de biblioteca, con sus condiciones de préstamo.
- **Inventario compartido:** los préstamos presenciales registrados por el personal y las solicitudes online deben actualizar las mismas existencias.
- **Reserva online:** una solicitud válida debe apartar una unidad de forma segura, evitando asignar el último ejemplar a dos personas.
- **Plazo de retiro:** el estudiante dispone de **24 horas desde que el administrador marca la solicitud como “Listo para retirar”**. El tiempo de preparación no consume ese plazo.
- **Vencimiento:** al cumplirse el plazo sin retiro, la reserva caduca y la unidad se libera. Repetir la acción “Listo para retirar” no debe reiniciar el contador.
- **Entrega:** retirar una unidad apartada cambia su estado a prestada sin descontarla de nuevo.
- **Devolución:** el personal registra la recepción y el estado del material antes de devolverlo a disponibilidad.
- **Inclusión:** un mismo recorrido accesible para toda la comunidad, con opciones de apoyo voluntarias y sin exigir diagnósticos para solicitar materiales.

El plazo de retiro es distinto de la duración del préstamo y de la anticipación de los avisos de devolución configurada mediante `DUE_SOON_HOURS`.

## Tecnologías

- **Backend:** Python 3.12 o superior y Flask.
- **Interfaz:** plantillas Jinja, HTML, CSS y JavaScript.
- **Persistencia local:** SQLite.
- **Despliegue:** Cloudflare Workers y D1.
- **Herramientas:** uv para las dependencias de Python y npm para las herramientas de despliegue.
- **Automatización:** GitHub Actions con un workflow de publicación manual.

Las dependencias y sus versiones se definen en [pyproject.toml](pyproject.toml), [uv.lock](uv.lock), [package.json](package.json) y [package-lock.json](package-lock.json).

## Ejecución local

### 1. Requisitos

Instala Git, Python 3.12 o superior y uv antes de comenzar.

### 2. Obtener el proyecto e instalar dependencias

```bash
git clone https://github.com/nDiaz231/IDS_PaginaWEB.git
cd IDS_PaginaWEB
uv sync --locked
```

### 3. Configurar el entorno

Genera una clave aleatoria:

```bash
uv run python -c "import secrets; print(secrets.token_hex(32))"
```

Crea un archivo `.env` en la raíz del proyecto y reemplaza el valor de `SECRET_KEY` por la clave generada:

```dotenv
APP_MODE=local
SECRET_KEY=REEMPLAZAR_POR_LA_CLAVE_GENERADA
DATABASE_PATH=instance/biblioteca.sqlite3
COOKIE_SECURE=0
TRUSTED_HOSTS=localhost,127.0.0.1
DUE_SOON_HOURS=48
```

La aplicación exige una clave de al menos 32 caracteres y rechaza valores que comiencen con `REEMPLAZAR`. Mantén `.env`, las bases de datos locales y sus respaldos fuera del control de versiones.

### 4. Inicializar una base de datos nueva

```bash
uv run flask --app app init-db
```

Este comando crea el esquema sin cuentas ni datos de ejemplo y no sobrescribe una base existente.

Para explorar el proyecto con datos de demostración, ejecuta lo siguiente sobre la base vacía:

```bash
uv run flask --app app seed-demo
```

El comando muestra las credenciales de demostración en la terminal. Estas cuentas son exclusivamente para uso local.

Como alternativa, crea una cuenta propia; el comando solicita la contraseña de forma interactiva:

```bash
uv run flask --app app create-user --email tu-correo@ucn.cl --name "Tu nombre" --role admin
```

### 5. Iniciar la aplicación

```bash
uv run flask --app app run
```

Abre [http://127.0.0.1:5000](http://127.0.0.1:5000). El servidor de desarrollo se utiliza para la ejecución local.

## Estructura del repositorio

```text
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
```

## Registro de alumnos

En la pantalla de acceso, **Crear cuenta** permite solicitar una cuenta con correo
`@alumnos.ucn.cl` o `@ce.ucn.cl`, nombre completo, RUT, año de ingreso y carrera.
La contraseña requiere al menos 8 caracteres, una mayúscula y un símbolo.
La cuenta permanece pendiente de validación institucional por administración;
comprobar el dominio y el dígito verificador no verifica identidad ni propiedad del correo.
Los datos se guardan en la base configurada, localmente durante esta etapa.
Consulta [la guía de pruebas y controles de seguridad](LOCAL_PREVIEW.md#registro-de-alumnos).

## Publicación

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