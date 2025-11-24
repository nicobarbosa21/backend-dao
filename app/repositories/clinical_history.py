import sqlite3
from datetime import datetime
from typing import Dict, List, Optional


def _normalize_fecha(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    try:
        return datetime.fromisoformat(str(value)).isoformat(sep=" ")
    except Exception:
        return None


def add_record(conn: sqlite3.Connection, data: Dict) -> int:
    cursor = conn.cursor()
    turno_id = data.get("turno_id")
    fecha_turno = _normalize_fecha(data.get("fecha_turno"))
    if turno_id and not fecha_turno:
        cursor.execute("SELECT fecha FROM turnos WHERE id = ?", (turno_id,))
        turno = cursor.fetchone()
        fecha_turno = turno["fecha"] if turno else None

    cursor.execute(
        """
        INSERT INTO historial_clinico (paciente_id, turno_id, descripcion, estado, fecha_turno)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            data["paciente_id"],
            turno_id,
            data["descripcion"],
            data.get("estado", "programado"),
            fecha_turno,
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    return new_id


def upsert_from_appointment(
    conn: sqlite3.Connection,
    turno_id: int,
    paciente_id: int,
    estado: str,
    fecha_turno,
    descripcion: Optional[str] = None,
    commit: bool = True,
) -> None:
    """Sincroniza el historial en base a un turno (crea o actualiza)."""
    cursor = conn.cursor()
    fecha_turno_norm = _normalize_fecha(fecha_turno)
    cursor.execute(
        "SELECT id, descripcion FROM historial_clinico WHERE turno_id = ?",
        (turno_id,),
    )
    existing = cursor.fetchone()
    note = descripcion or (existing["descripcion"] if existing else "Seguimiento de turno")

    if existing:
        cursor.execute(
            """
            UPDATE historial_clinico
            SET estado = ?, fecha_turno = ?, descripcion = ?
            WHERE turno_id = ?
            """,
            (estado, fecha_turno_norm, note, turno_id),
        )
    else:
        cursor.execute(
            """
            INSERT INTO historial_clinico (paciente_id, turno_id, descripcion, estado, fecha_turno)
            VALUES (?, ?, ?, ?, ?)
            """,
            (paciente_id, turno_id, note, estado, fecha_turno_norm),
        )
    if commit:
        conn.commit()
    cursor.close()


def list_records(conn: sqlite3.Connection, paciente_id: Optional[int]) -> List[dict]:
    cursor = conn.cursor()
    base_query = """
        SELECT
            h.id,
            h.paciente_id,
            h.turno_id,
            h.descripcion,
            h.estado,
            h.fecha_turno,
            m.nombre as medico_nombre,
            m.apellido as medico_apellido,
            e.nombre as especialidad
        FROM historial_clinico h
        LEFT JOIN turnos t ON h.turno_id = t.id
        LEFT JOIN medicos m ON t.medico_id = m.id
        LEFT JOIN especialidades e ON m.especialidad_id = e.id
    """
    params = ()
    if paciente_id is not None:
        base_query += " WHERE h.paciente_id = ?"
        params = (paciente_id,)
    base_query += " ORDER BY datetime(h.fecha_turno) DESC, h.id DESC"
    cursor.execute(base_query, params)
    rows = cursor.fetchall()
    cursor.close()
    return [dict(row) for row in rows]
