import os
import sqlite3
import threading
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

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
                    "DATABASE_URL", str(Path("data") / "clinic.db")
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
    conn.commit()

    # Datos minimos de prueba si la base esta vacia.
    cursor.execute("SELECT COUNT(*) as total FROM especialidades")
    if cursor.fetchone()["total"] == 0:
        cursor.executemany(
            "INSERT INTO especialidades (nombre) VALUES (?)",
            [("Clinica",), ("Pediatria",), ("Cardiologia",)],
        )
    cursor.execute("SELECT COUNT(*) as total FROM pacientes")
    if cursor.fetchone()["total"] == 0:
        cursor.executemany(
            "INSERT INTO pacientes (dni, nombre, apellido, mail) VALUES (?, ?, ?, ?)",
            [
                ("30111222", "Ana", "Garcia", "ana@example.com"),
                ("28999111", "Luis", "Perez", "luis@example.com"),
            ],
        )
    cursor.execute("SELECT COUNT(*) as total FROM medicos")
    if cursor.fetchone()["total"] == 0:
        # Asigna especialidades existentes.
        cursor.execute("SELECT id FROM especialidades WHERE nombre = ?", ("Clinica",))
        esp_clinica = cursor.fetchone()["id"]
        cursor.execute("SELECT id FROM especialidades WHERE nombre = ?", ("Pediatria",))
        esp_ped = cursor.fetchone()["id"]
        cursor.executemany(
            "INSERT INTO medicos (nombre, apellido, especialidad_id, mail) VALUES (?, ?, ?, ?)",
            [
                ("Mariana", "Suarez", esp_clinica, "mariana.suarez@example.com"),
                ("Diego", "Lopez", esp_ped, "diego.lopez@example.com"),
            ],
        )
    cursor.execute("SELECT COUNT(*) as total FROM disponibilidad_medicos")
    if cursor.fetchone()["total"] == 0:
        # Horarios de ejemplo para medicos semilla.
        cursor.execute("SELECT id FROM medicos WHERE apellido = ?", ("Suarez",))
        medico1 = cursor.fetchone()
        cursor.execute("SELECT id FROM medicos WHERE apellido = ?", ("Lopez",))
        medico2 = cursor.fetchone()
        today = date.today()
        if medico1:
            cursor.executemany(
                """
                INSERT INTO disponibilidad_medicos (medico_id, fecha, hora_inicio, hora_fin)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (medico1["id"], _next_weekday(today, 0).isoformat(), "09:00", "12:00"),
                    (medico1["id"], _next_weekday(today, 2).isoformat(), "14:00", "18:00"),
                ],
            )
        if medico2:
            cursor.executemany(
                """
                INSERT INTO disponibilidad_medicos (medico_id, fecha, hora_inicio, hora_fin)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (medico2["id"], _next_weekday(today, 1).isoformat(), "10:00", "13:00"),
                    (medico2["id"], _next_weekday(today, 3).isoformat(), "09:00", "12:00"),
                ],
            )
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
