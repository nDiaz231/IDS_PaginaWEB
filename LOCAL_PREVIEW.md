# Vista local de BiblioUCN

Desde esta carpeta, ejecuta en PowerShell:

```powershell
& .venv/Scripts/python.exe run_local.py
```

Abre http://127.0.0.1:5000. Solo escucha en este equipo y no publica en Cloudflare.
El lanzador crea una base ficticia independiente en `instance/demo.sqlite3` la primera vez.

- Administrador: `admin@demo.test`
- Estudiante: `ana@demo.test`
- Clave de ambas cuentas de demostración: `DemoUCN2026!`

## Primer avance: retiro en 24 horas

En Solicitudes, abre una solicitud aprobada y marca «Confirmar listo para retiro».
Desde ese instante hay 24 horas corridas; la fecha límite aparece en el detalle y listado.
La preparación no consume plazo y una segunda confirmación no lo reinicia.
Una reserva vencida se conserva como cancelación automática con motivo y evento de auditoría.
Su ejemplar se libera y no puede entregarse con esa reserva.

La demo procesa vencimientos cada 30 segundos y antes de atender las páginas.
Las operaciones de escritura también revisan vencimientos dentro de la transacción.
Una página ya abierta requiere actualizarse para mostrar los cambios.
Los avisos son internos a la aplicación; no se envían correos.

Para otros despliegues está disponible `flask --app app expire-pickups`.
Cloudflare todavía requiere configurar y validar una ejecución periódica equivalente;
el hilo de mantenimiento de esta demo no se ejecuta en Workers.

## Duración elegida por el estudiante

Las nuevas solicitudes piden una cantidad entera de días: de 1 a 14 en alta
demanda y de 1 a 30 en baja demanda (colección general). En este prototipo,
«un mes» significa 30 días. La fecha se calcula desde la entrega; la espera
de preparación y retiro no consume el préstamo. El administrador puede
adelantar la devolución, pero no exceder el plazo elegido.

Las solicitudes antiguas mantienen su historial y muestran «duración no indicada».
El lanzador migra la base local a versión 3 con un respaldo previo en
`instance/backups/`. Los préstamos ya entregados conservan su vencimiento.
Para Cloudflare se incluye la migración `0002_requested_days.sql`, aún sin publicar.

## Pruebas

```powershell
& .venv/Scripts/python.exe -m unittest discover -s tests -v
```

Esta entrega no implementa aún asignación automática al solicitar, préstamos presenciales
en un paso ni el catálogo de juegos y materiales. Conserva el flujo de aprobación existente.


## Libros y utilidades

La navegación separa Libros y Utilidades. Utilidades incluye juegos de mesa,
plumones, cables, laptops y cargadores; cada unidad mantiene su disponibilidad,
solicitudes, préstamos, favoritos y avisos. El administrador puede crear artículos
y gestionar unidades. Por ahora se aplican los plazos y cupos existentes según
la colección de demanda; falta acordar políticas específicas para cada material.

La migración 4 conserva los libros existentes y crea un respaldo al actualizar.
El lanzador local añade una sola vez siete artículos ficticios de utilidades,
identificados como demostración. Esta carga no se ejecuta en producción.


## Registro de alumnos

Desde Iniciar sesión, el botón Crear cuenta abre `/crear-cuenta`.
Solo acepta `@alumnos.ucn.cl` y `@ce.ucn.cl`, sin subdominios ni sufijos adicionales.
Pide nombre completo, RUT con dígito verificador, año de ingreso, carrera,
contraseña (8–200 caracteres, una mayúscula y un símbolo) y confirmación.

El registro persiste en `instance/demo.sqlite3`, independiente del repositorio.
La cuenta queda inactiva y sin préstamos hasta revisión. Entra como administrador,
abre Alumnos → Revisar registro y confirma identidad, datos y titularidad del correo
por un canal institucional antes de habilitar. Cambiar la habilitación o la clave
no permite saltarse esa revisión. No hay envío automático de correos.
Las cuentas antiguas y de demostración se conservan.

La migración 5 genera un respaldo previo. La migración equivalente para D1 está
preparada, pero aún no se han conectado ni publicado servicios en la nube.

### Controles del registro

- Validación en servidor; consultas con parámetros; salida HTML escapada.
- RUT único normalizado; correo único sin distinguir mayúsculas.
- Cuenta nueva siempre alumno, sin permisos tomados del formulario.
- Contraseñas PBKDF2-HMAC-SHA256 con sal y 600 000 iteraciones; nunca texto plano.
  El formato de Workers añade un pepper y sigue aceptando hashes antiguos.
- CSRF, cookies HttpOnly/SameSite, CSP y respuestas privadas sin caché.
- Límites persistentes por origen: 5 intentos/15 min y 30/día; globales:
  50/15 min y 500/día. Se aplican antes de derivar la contraseña. No confía en
  cabeceras IP enviadas directamente al servidor local.
- Formularios de hasta 64 KiB, 20 partes y campos multipart de hasta 16 KiB.
- Respuesta genérica para correos o RUT ya existentes. No reemplaza sus datos.
- Perfil privado accesible solo a administración; no se incluyen RUT ni claves
  en cookies o auditoría. Las bases y respaldos deben mantenerse fuera de Git.

Estos controles reducen abuso; no garantizan inmunidad a exploits o DDoS.
Para publicar faltan HTTPS, configuración real de D1, WAF y límites en el borde,
verificación de correo o revisión institucional operativa, monitoreo y respaldo
con acceso restringido. El adaptador D1 actual carga un snapshot con un límite
pequeño de filas y requiere revisión de escalabilidad antes de uso masivo.

Referencias consultadas: [OWASP: validación y verificación de correo](https://cheatsheetseries.owasp.org/cheatsheets/Email_Validation_and_Verification_Cheat_Sheet.html),
[almacenamiento de contraseñas](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
y [seguridad de Flask](https://flask.palletsprojects.com/en/stable/web-security/).
