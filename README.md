# MediFlow API

## Instalacion y ejecucion
```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```
Swagger disponible en `/docs`.

## Autenticacion
- Login: `POST /auth/login` con JSON `{"username": "admin", "password": "admin123"}` (password inicial configurable con `ADMIN_DEFAULT_PASSWORD`).
- Todas las rutas (excepto `/health` y `/auth/login`) exigen `Authorization: Bearer <token>`.
- Variables: `SECRET_KEY`, `PASSWORD_SALT`, `ACCESS_TOKEN_EXPIRE_MINUTES`.
- Emails: `SMTP_SERVER`/`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`/`SMTP_USER`, `SMTP_PASSWORD`/`SMTP_PASS`, `EMAIL_SENDER`, `SMTP_USE_SSL` (auto true si puerto 465), `SMTP_DRY_RUN` (default `true`).

## Tests
```bash
python -m pytest
```
Incluye pruebas de autenticacion, reglas de turnos y CRUD de pacientes. Cada test usa una base SQLite temporal.

## Turnos y disponibilidad
- Cada disponibilidad (`disponibilidad_medicos`) tiene flag `activa` y se marca en 0 al asignarla a un turno.
- La disponibilidad se define por fecha (YYYY-MM-DD) + hora_inicio/hora_fin. Un turno debe usar un `disponibilidad_id` cuya fecha coincida con la fecha solicitada; la hora inicio/fin de la disponibilidad define la duracion.
- Si el turno se cancela, la disponibilidad vuelve a `activa` y puede asignarse nuevamente.
- No se permiten turnos en fechas/horarios pasados.

## Configuracion via .env
Crea un archivo `.env` en la raiz con, por ejemplo:
```
DATABASE_URL=data/clinic.db
SECRET_KEY=changeme
PASSWORD_SALT=changeme
ACCESS_TOKEN_EXPIRE_MINUTES=60

SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USER=mediflow@gmail.com
SMTP_PASS=ppgi lauj rkcn lcnh
SMTP_USE_SSL=true
SMTP_DRY_RUN=false
EMAIL_SENDER=mediflow@gmail.com
```
Las variables del `.env` se cargan automaticamente al iniciar la app.

## Arquitectura y patrones
- **Singleton**: conexion SQLite en `app/db.py` (una sola conexion por proceso).
- **Repositorio (SQL crudo con cursor)**: `app/repositories/*` para todos los ABMC y logica de turnos.
- **Observer**: recordatorios por mail en `app/services/reminder.py` + `app/observers/base.py`.
- **Capa de seguridad**: JWT simple en `app/security.py` y middleware en `app/main.py`.
- **Reportes**: calculos agregados en `app/services/reports.py`.

## CI/CD
- GitHub Actions (`.github/workflows/ci.yml`): en cada push/PR se instala y ejecuta `python -m pytest`. Solo integra si los tests pasan.

## Datos de ejemplo
Se crean pacientes, medicos, especialidades, disponibilidades y el usuario admin por defecto en el arranque (`init_db`).
