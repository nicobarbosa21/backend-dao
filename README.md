# Consultorio Medico

## Instalación y ejecución
```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```
Swagger disponible en `/docs`.

## Autenticación
- Login: `POST /auth/login` con JSON `{"username": "admin", "password": "admin123"}` (password inicial configurable con `ADMIN_DEFAULT_PASSWORD`).
- Todas las rutas (excepto `/health` y `/auth/login`) exigen `Authorization: Bearer <token>`.
- Variables: `SECRET_KEY`, `PASSWORD_SALT`, `ACCESS_TOKEN_EXPIRE_MINUTES`.

## Tests
```bash
python -m pytest
```
Incluye pruebas de autenticación, reglas de turnos (disponibilidad/solapamiento) y CRUD de pacientes. Cada test usa una base SQLite temporal.

## Arquitectura y patrones
- **Singleton**: conexión SQLite en `app/db.py` (una sola conexión por proceso).
- **Repositorio (SQL crudo con cursor)**: `app/repositories/*` para todos los ABMC y lógica de turnos.
- **Observer**: recordatorios por mail en `app/services/reminder.py` + `app/observers/base.py`.
- **Capa de seguridad**: JWT simple en `app/security.py` y middleware en `app/main.py`.
- **Reportes**: cálculos agregados en `app/services/reports.py`.

## CI/CD
- GitHub Actions (`.github/workflows/ci.yml`): en cada push/PR se instala y ejecuta `python -m pytest`. Solo integra si los tests pasan.

## Datos de ejemplo
Se crean pacientes, médicos, especialidades, disponibilidades y el usuario admin por defecto en el arranque (`init_db`).
