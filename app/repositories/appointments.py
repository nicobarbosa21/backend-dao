import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


def _validate_doctor_availability(
    conn: sqlite3.Connection, medico_id: int, start: datetime, duration_minutes: int
) -> Tuple[bool, str]:
    """Valida que el turno esté dentro del horario y sin superposición."""
    day = start.weekday()  # 0=lunes
    time_str = start.strftime("%H:%M")
    end_time_str = (start + timedelta(minutes=duration_minutes)).strftime("%H:%M")

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT hora_inicio, hora_fin
        FROM disponibilidad_medicos
        WHERE medico_id = ? AND dia_semana = ?
          AND hora_inicio <= ? AND hora_fin >= ?
        """,
        (medico_id, day, time_str, end_time_str),
    )
    availability = cursor.fetchone()
    if not availability:
        cursor.close()
        return False, "El médico no tiene disponibilidad en ese horario."

    cursor.execute(
        """
        SELECT id, fecha, duracion, estado
        FROM turnos
        WHERE medico_id = ? AND estado != 'cancelado'
        """,
        (medico_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    new_start = start
    new_end = start + timedelta(minutes=duration_minutes)
    for row in rows:
        existing_start = datetime.fromisoformat(row["fecha"])
        existing_end = existing_start + timedelta(minutes=row["duracion"])
        # Chequeo de solapamiento: start < other_end y end > other_start
        if new_start < existing_end and new_end > existing_start:
            return False, "El médico ya tiene un turno asignado en ese horario."
    return True, ""


def create_appointment(conn: sqlite3.Connection, data: Dict) -> int:
    start_dt: datetime = data["fecha"]
    duration: int = data["duracion"]
    is_available, reason = _validate_doctor_availability(
        conn, data["medico_id"], start_dt, duration
    )
    if not is_available:
        raise ValueError(reason)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO turnos (paciente_id, medico_id, fecha, estado, motivo_consulta, duracion, recordatorio)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["paciente_id"],
            data["medico_id"],
            start_dt.isoformat(sep=" "),
            data["estado"],
            data.get("motivo_consulta"),
            duration,
            "pendiente",
        ),
    )
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    return new_id


def list_appointments(conn: sqlite3.Connection, medico_id: Optional[int] = None) -> List[dict]:
    cursor = conn.cursor()
    if medico_id:
        cursor.execute(
            """
            SELECT t.*, p.nombre as paciente_nombre, p.apellido as paciente_apellido
            FROM turnos t
            JOIN pacientes p ON t.paciente_id = p.id
            WHERE t.medico_id = ?
            ORDER BY datetime(t.fecha)
            """,
            (medico_id,),
        )
    else:
        cursor.execute(
            """
            SELECT t.*, p.nombre as paciente_nombre, p.apellido as paciente_apellido, m.nombre as medico_nombre, m.apellido as medico_apellido
            FROM turnos t
            JOIN pacientes p ON t.paciente_id = p.id
            JOIN medicos m ON t.medico_id = m.id
            ORDER BY datetime(t.fecha)
            """
        )
    rows = cursor.fetchall()
    cursor.close()
    return [dict(row) for row in rows]


def update_status(conn: sqlite3.Connection, appointment_id: int, estado: str) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE turnos SET estado = ? WHERE id = ?",
        (estado, appointment_id),
    )
    conn.commit()
    updated = cursor.rowcount > 0
    cursor.close()
    return updated


def get_appointment(conn: sqlite3.Connection, appointment_id: int) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT t.*, p.mail as paciente_mail, p.nombre as paciente_nombre, p.apellido as paciente_apellido
        FROM turnos t
        JOIN pacientes p ON t.paciente_id = p.id
        WHERE t.id = ?
        """,
        (appointment_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    return dict(row) if row else None
