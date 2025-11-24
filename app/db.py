import os
import sqlite3
import threading
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import List, Optional

from app.security import hash_password


class Database:
    """Singleton para manejar una unica conexion a la BD."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: Optional[str] = None):
        # Soporta reinicializar con otro path llamando a reset_instance.
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.db_path = db_path or os.getenv(
                    "DATABASE_URL", str(Path("data") / "mediflow.db")
                )
                Path(cls._instance.db_path).parent.mkdir(parents=True, exist_ok=True)
                cls._instance.conn = sqlite3.connect(
                    cls._instance.db_path,
                    check_same_thread=False,
                    detect_types=sqlite3.PARSE_DECLTYPES,
                )
                cls._instance.conn.row_factory = sqlite3.Row
            return cls._instance

    @property
    def connection(self) -> sqlite3.Connection:
        return self.conn

    def close(self) -> None:
        try:
            self.conn.close()
        finally:
            type(self)._instance = None

    @classmethod
    def reset_instance(cls, db_path: Optional[str] = None) -> "Database":
        """Permite crear una nueva conexion (util en tests)."""
        if cls._instance:
            try:
                cls._instance.conn.close()
            except Exception:
                pass
        cls._instance = None
        return cls(db_path)


def _next_weekday(start: date, weekday: int) -> date:
    """Devuelve la proxima fecha (incluyendo hoy) del weekday (0=lunes)."""
    days_ahead = (weekday - start.weekday()) % 7
    return start + timedelta(days=days_ahead)


def init_db() -> None:
    db = Database()
    conn = db.connection
    cursor = conn.cursor()
    cursor.executescript(
        """
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dni TEXT NOT NULL UNIQUE,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            mail TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS especialidades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS medicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            especialidad_id INTEGER NOT NULL,
            mail TEXT NOT NULL,
            FOREIGN KEY (especialidad_id) REFERENCES especialidades(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS disponibilidad_medicos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medico_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fin TEXT NOT NULL,
            activa INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (medico_id) REFERENCES medicos(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS turnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            medico_id INTEGER NOT NULL,
            disponibilidad_id INTEGER,
            fecha TEXT NOT NULL,
            estado TEXT NOT NULL,
            motivo_consulta TEXT,
            duracion INTEGER NOT NULL,
            recordatorio TEXT,
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE,
            FOREIGN KEY (medico_id) REFERENCES medicos(id) ON DELETE CASCADE,
            FOREIGN KEY (disponibilidad_id) REFERENCES disponibilidad_medicos(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS historial_clinico (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            turno_id INTEGER,
            descripcion TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'programado',
            fecha_turno TEXT,
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE,
            FOREIGN KEY (turno_id) REFERENCES turnos(id) ON DELETE SET NULL
        );
        CREATE TABLE IF NOT EXISTS recetas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medico_id INTEGER NOT NULL,
            paciente_id INTEGER NOT NULL,
            descripcion TEXT NOT NULL,
            FOREIGN KEY (medico_id) REFERENCES medicos(id) ON DELETE CASCADE,
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_turnos_medico_fecha ON turnos(medico_id, fecha);
        CREATE INDEX IF NOT EXISTS idx_historial_paciente ON historial_clinico(paciente_id);
        CREATE INDEX IF NOT EXISTS idx_historial_turno ON historial_clinico(turno_id);
        """
    )

    def _column_exists(table: str, column: str) -> bool:
        cursor.execute(f"PRAGMA table_info({table})")
        return any(row["name"] == column for row in cursor.fetchall())

    # Migraciones livianas para entornos ya creados.
    if not _column_exists("disponibilidad_medicos", "activa"):
        cursor.execute(
            "ALTER TABLE disponibilidad_medicos ADD COLUMN activa INTEGER NOT NULL DEFAULT 1"
        )
    if not _column_exists("turnos", "disponibilidad_id"):
        cursor.execute("ALTER TABLE turnos ADD COLUMN disponibilidad_id INTEGER")
    if not _column_exists("disponibilidad_medicos", "fecha"):
        cursor.execute("ALTER TABLE disponibilidad_medicos ADD COLUMN fecha TEXT")
        conn.commit()
        cursor.execute("SELECT id, dia_semana FROM disponibilidad_medicos")
        rows = cursor.fetchall()
        today = date.today()
        for row in rows:
            if row["dia_semana"] is None:
                continue
            target = _next_weekday(today, int(row["dia_semana"]))
            cursor.execute(
                "UPDATE disponibilidad_medicos SET fecha = ? WHERE id = ?",
                (target.isoformat(), row["id"]),
            )
    if not _column_exists("historial_clinico", "estado"):
        cursor.execute("ALTER TABLE historial_clinico ADD COLUMN estado TEXT DEFAULT 'programado'")
        cursor.execute("UPDATE historial_clinico SET estado = 'programado' WHERE estado IS NULL")
    if not _column_exists("historial_clinico", "fecha_turno"):
        cursor.execute("ALTER TABLE historial_clinico ADD COLUMN fecha_turno TEXT")
    conn.commit()

    # Datos de prueba enriquecidos si la base esta vacia.
    cursor.execute("SELECT COUNT(*) as total FROM especialidades")
    if cursor.fetchone()["total"] == 0:
        specialties = [
            "Clinica",
            "Pediatria",
            "Cardiologia",
            "Dermatologia",
            "Traumatologia",
            "Neurologia",
        ]
        cursor.executemany(
            "INSERT INTO especialidades (nombre) VALUES (?)",
            [(name,) for name in specialties],
        )

    cursor.execute("SELECT id, nombre FROM especialidades")
    specialties_map = {row["nombre"]: row["id"] for row in cursor.fetchall()}

    cursor.execute("SELECT COUNT(*) as total FROM pacientes")
    if cursor.fetchone()["total"] == 0:
        patients_seed = [
            ("30111222", "Ana", "Garcia", "ana@mediflow.test"),
            ("28999111", "Luis", "Perez", "luis@mediflow.test"),
            ("33001888", "Sofia", "Martinez", "sofia@mediflow.test"),
            ("31222333", "Carlos", "Ramos", "carlos@mediflow.test"),
            ("27888999", "Valeria", "Torres", "valeria@mediflow.test"),
            ("35444999", "Matias", "Rios", "matias@mediflow.test"),
            ("32555111", "Carla", "Diaz", "carla@mediflow.test"),
            ("36666111", "Nicolas", "Fernandez", "nicolas@mediflow.test"),
        ]
        cursor.executemany(
            "INSERT INTO pacientes (dni, nombre, apellido, mail) VALUES (?, ?, ?, ?)",
            patients_seed,
        )
    cursor.execute("SELECT id, mail FROM pacientes")
    patients_map = {row["mail"]: row["id"] for row in cursor.fetchall()}

    cursor.execute("SELECT COUNT(*) as total FROM medicos")
    if cursor.fetchone()["total"] == 0:
        doctors_seed = [
            ("Mariana", "Suarez", "Clinica", "mariana.suarez@mediflow.com"),
            ("Diego", "Lopez", "Pediatria", "diego.lopez@mediflow.com"),
            ("Lucia", "Gimenez", "Cardiologia", "lucia.gimenez@mediflow.com"),
            ("Martin", "Rios", "Dermatologia", "martin.rios@mediflow.com"),
            ("Laura", "Castro", "Traumatologia", "laura.castro@mediflow.com"),
        ]
        for nombre, apellido, especialidad, mail in doctors_seed:
            esp_id = specialties_map.get(especialidad)
            if esp_id:
                cursor.execute(
                    "INSERT INTO medicos (nombre, apellido, especialidad_id, mail) VALUES (?, ?, ?, ?)",
                    (nombre, apellido, esp_id, mail),
                )
    cursor.execute("SELECT id, apellido FROM medicos")
    doctors_map = {row["apellido"]: row["id"] for row in cursor.fetchall()}

    availability_rows: List[dict] = []
    cursor.execute("SELECT COUNT(*) as total FROM disponibilidad_medicos")
    if cursor.fetchone()["total"] == 0:
        today = date.today()
        availability_seed = [
            {"doctor": "Suarez", "fecha": _next_weekday(today, 0), "inicio": "09:00", "fin": "12:00"},
            {"doctor": "Suarez", "fecha": _next_weekday(today, 2), "inicio": "14:00", "fin": "17:00"},
            {"doctor": "Lopez", "fecha": _next_weekday(today, 1), "inicio": "10:00", "fin": "13:00"},
            {"doctor": "Lopez", "fecha": _next_weekday(today, 4), "inicio": "09:00", "fin": "11:00"},
            {"doctor": "Gimenez", "fecha": _next_weekday(today, 3), "inicio": "08:30", "fin": "12:00"},
            {"doctor": "Gimenez", "fecha": _next_weekday(today, 5), "inicio": "14:00", "fin": "17:00"},
            {"doctor": "Rios", "fecha": _next_weekday(today, 2), "inicio": "16:00", "fin": "19:00"},
            {"doctor": "Rios", "fecha": _next_weekday(today, 5), "inicio": "08:00", "fin": "10:00"},
            {"doctor": "Castro", "fecha": _next_weekday(today, 1), "inicio": "08:00", "fin": "12:00"},
            {"doctor": "Castro", "fecha": _next_weekday(today, 4), "inicio": "13:00", "fin": "16:00"},
        ]
        for slot in availability_seed:
            medico_id = doctors_map.get(slot["doctor"])
            if not medico_id:
                continue
            cursor.execute(
                """
                INSERT INTO disponibilidad_medicos (medico_id, fecha, hora_inicio, hora_fin)
                VALUES (?, ?, ?, ?)
                """,
                (medico_id, slot["fecha"].isoformat(), slot["inicio"], slot["fin"]),
            )
            availability_rows.append(
                {
                    "id": cursor.lastrowid,
                    "medico_id": medico_id,
                    "fecha": slot["fecha"].isoformat(),
                    "hora_inicio": slot["inicio"],
                    "hora_fin": slot["fin"],
                }
            )
    else:
        cursor.execute("SELECT id, medico_id, fecha, hora_inicio, hora_fin, activa FROM disponibilidad_medicos")
        availability_rows = [dict(row) for row in cursor.fetchall()]

    cursor.execute("SELECT COUNT(*) as total FROM turnos")
    if cursor.fetchone()["total"] == 0:
        from app.repositories import clinical_history

        now = datetime.now()
        availability_by_doctor = {}
        for row in availability_rows:
            availability_by_doctor.setdefault(row["medico_id"], []).append(row)
        for slots in availability_by_doctor.values():
            slots.sort(key=lambda r: (r["fecha"], r["hora_inicio"]))

        appointments_seed = [
            {
                "patient": "ana@mediflow.test",
                "doctor": "Suarez",
                "days_offset": -15,
                "hour": 9,
                "minute": 0,
                "estado": "completado",
                "motivo": "Control anual",
            },
            {
                "patient": "luis@mediflow.test",
                "doctor": "Lopez",
                "days_offset": -7,
                "hour": 10,
                "minute": 30,
                "estado": "ausente",
                "motivo": "Consulta pediatrica",
            },
            {
                "patient": "sofia@mediflow.test",
                "doctor": "Gimenez",
                "days_offset": -2,
                "hour": 11,
                "minute": 0,
                "estado": "completado",
                "motivo": "Chequeo cardiologico",
            },
            {
                "patient": "carlos@mediflow.test",
                "doctor": "Rios",
                "days_offset": -1,
                "hour": 16,
                "minute": 0,
                "estado": "cancelado",
                "motivo": "Dermatitis",
            },
            {
                "patient": "valeria@mediflow.test",
                "doctor": "Castro",
                "availability_index": 0,
                "estado": "programado",
                "motivo": "Dolor de rodilla",
            },
            {
                "patient": "matias@mediflow.test",
                "doctor": "Suarez",
                "availability_index": 1,
                "estado": "programado",
                "motivo": "Seguimiento clinico",
            },
            {
                "patient": "carla@mediflow.test",
                "doctor": "Lopez",
                "availability_index": 1,
                "estado": "programado",
                "motivo": "Control pediatrico",
            },
            {
                "patient": "nicolas@mediflow.test",
                "doctor": "Gimenez",
                "availability_index": 1,
                "estado": "programado",
                "motivo": "Chequeo de hipertension",
            },
            {
                "patient": "valeria@mediflow.test",
                "doctor": "Rios",
                "days_offset": -20,
                "hour": 15,
                "minute": 0,
                "estado": "completado",
                "motivo": "Lesion cutanea",
            },
            {
                "patient": "ana@mediflow.test",
                "doctor": "Castro",
                "days_offset": -9,
                "hour": 17,
                "minute": 0,
                "estado": "completado",
                "motivo": "Rehabilitacion",
            },
        ]

        for appt in appointments_seed:
            paciente_id = patients_map.get(appt["patient"])
            medico_id = doctors_map.get(appt["doctor"])
            if not paciente_id or not medico_id:
                continue

            availability_id = None
            duration = appt.get("duracion", 45)
            if "availability_index" in appt:
                slots = availability_by_doctor.get(medico_id, [])
                idx = appt.get("availability_index", 0)
                if 0 <= idx < len(slots):
                    slot = slots[idx]
                    availability_id = slot["id"]
                    appt_dt = datetime.fromisoformat(f"{slot['fecha']} {slot['hora_inicio']}")
                    try:
                        start_t = datetime.strptime(slot["hora_inicio"], "%H:%M").time()
                        end_t = datetime.strptime(slot["hora_fin"], "%H:%M").time()
                        duration = int(
                            (datetime.combine(date.today(), end_t) - datetime.combine(date.today(), start_t)).total_seconds()
                            // 60
                        )
                    except Exception:
                        duration = appt.get("duracion", 60)
                else:
                    appt_dt = datetime.combine(
                        now.date() + timedelta(days=appt.get("days_offset", 2)),
                        time(appt.get("hour", 9), appt.get("minute", 0)),
                    )
            else:
                appt_dt = datetime.combine(
                    now.date() + timedelta(days=appt["days_offset"]),
                    time(appt["hour"], appt["minute"]),
                )

            cursor.execute(
                """
                INSERT INTO turnos (paciente_id, medico_id, disponibilidad_id, fecha, estado, motivo_consulta, duracion, recordatorio)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    paciente_id,
                    medico_id,
                    availability_id,
                    appt_dt.isoformat(sep=" "),
                    appt["estado"],
                    appt.get("motivo"),
                    duration,
                    "semilla",
                ),
            )
            turno_id = cursor.lastrowid
            if availability_id:
                cursor.execute(
                    "UPDATE disponibilidad_medicos SET activa = 0 WHERE id = ?",
                    (availability_id,),
                )
            clinical_history.upsert_from_appointment(
                conn,
                turno_id=turno_id,
                paciente_id=paciente_id,
                estado=appt["estado"],
                fecha_turno=appt_dt,
                descripcion=appt.get("motivo") or "Turno",
                commit=False,
            )
        conn.commit()

    cursor.execute("SELECT COUNT(*) as total FROM admins")
    if cursor.fetchone()["total"] == 0:
        default_password = os.getenv("ADMIN_DEFAULT_PASSWORD", "admin123")
        cursor.execute(
            "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
            ("admin", hash_password(default_password)),
        )
    conn.commit()
    cursor.close()


def get_connection() -> sqlite3.Connection:
    return Database().connection
