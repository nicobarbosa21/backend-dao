import os
import sqlite3
import threading
from pathlib import Path
from typing import Optional

from app.security import hash_password


class Database:
    """Singleton para manejar una única conexión a la BD."""

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
        """Permite crear una nueva conexión (útil en tests)."""
        if cls._instance:
            try:
                cls._instance.conn.close()
            except Exception:
                pass
        cls._instance = None
        return cls(db_path)


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
            dia_semana INTEGER NOT NULL,
            hora_inicio TEXT NOT NULL,
            hora_fin TEXT NOT NULL,
            FOREIGN KEY (medico_id) REFERENCES medicos(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS turnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            medico_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            estado TEXT NOT NULL,
            motivo_consulta TEXT,
            duracion INTEGER NOT NULL,
            recordatorio TEXT,
            FOREIGN KEY (paciente_id) REFERENCES pacientes(id) ON DELETE CASCADE,
            FOREIGN KEY (medico_id) REFERENCES medicos(id) ON DELETE CASCADE
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
    conn.commit()

    # Datos mínimos de prueba si la base está vacía.
    cursor.execute("SELECT COUNT(*) as total FROM especialidades")
    if cursor.fetchone()["total"] == 0:
        cursor.executemany(
            "INSERT INTO especialidades (nombre) VALUES (?)",
            [("Clínica",), ("Pediatría",), ("Cardiología",)],
        )
    cursor.execute("SELECT COUNT(*) as total FROM pacientes")
    if cursor.fetchone()["total"] == 0:
        cursor.executemany(
            "INSERT INTO pacientes (dni, nombre, apellido, mail) VALUES (?, ?, ?, ?)",
            [
                ("30111222", "Ana", "García", "ana@example.com"),
                ("28999111", "Luis", "Pérez", "luis@example.com"),
            ],
        )
    cursor.execute("SELECT COUNT(*) as total FROM medicos")
    if cursor.fetchone()["total"] == 0:
        # Asigna especialidades existentes.
        cursor.execute("SELECT id FROM especialidades WHERE nombre = ?", ("Clínica",))
        esp_clinica = cursor.fetchone()["id"]
        cursor.execute("SELECT id FROM especialidades WHERE nombre = ?", ("Pediatría",))
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
        # Horarios de ejemplo para médicos semilla.
        cursor.execute("SELECT id FROM medicos WHERE apellido = ?", ("Suarez",))
        medico1 = cursor.fetchone()
        cursor.execute("SELECT id FROM medicos WHERE apellido = ?", ("Lopez",))
        medico2 = cursor.fetchone()
        if medico1:
            cursor.executemany(
                """
                INSERT INTO disponibilidad_medicos (medico_id, dia_semana, hora_inicio, hora_fin)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (medico1["id"], 0, "09:00", "12:00"),
                    (medico1["id"], 2, "14:00", "18:00"),
                ],
            )
        if medico2:
            cursor.executemany(
                """
                INSERT INTO disponibilidad_medicos (medico_id, dia_semana, hora_inicio, hora_fin)
                VALUES (?, ?, ?, ?)
                """,
                [
                    (medico2["id"], 1, "10:00", "13:00"),
                    (medico2["id"], 3, "09:00", "12:00"),
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
