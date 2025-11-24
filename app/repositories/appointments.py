import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from app.repositories import clinical_history


def _validate_slot_selection(
    conn: sqlite3.Connection, medico_id: int, availability_id: int, target_date: datetime
) -> Tuple[bool, Optional[datetime], Optional[int], str]:
    """Valida que la disponibilidad exista, pertenezca al medico y este libre."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, medico_id, fecha, hora_inicio, hora_fin, activa
        FROM disponibilidad_medicos
        WHERE id = ?
        """,
        (availability_id,),
    )
    availability = cursor.fetchone()
    if not availability:
        cursor.close()
        return False, None, None, "Disponibilidad inexistente."
    if availability["medico_id"] != medico_id:
        cursor.close()
        return False, None, None, "La disponibilidad no pertenece al medico."
    if availability["activa"] == 0:
        cursor.close()
        return False, None, None, "La disponibilidad ya fue asignada a otro turno."
    if not availability["fecha"]:
        cursor.close()
        return False, None, None, "La disponibilidad no tiene fecha asignada."

    try:
        availability_date = datetime.strptime(availability["fecha"], "%Y-%m-%d").date()
    except ValueError:
        cursor.close()
        return False, None, None, "Formato de fecha de disponibilidad invalido."

    if target_date.date() != availability_date:
        cursor.close()
        return False, None, None, "La fecha no coincide con la disponibilidad."

    cursor.execute(
        """
        SELECT id FROM turnos
        WHERE disponibilidad_id = ? AND estado != 'cancelado'
        """,
        (availability_id,),
    )
    if cursor.fetchone():
        cursor.close()
        return False, None, None, "La disponibilidad ya fue asignada a otro turno."

    try:
        start_time = datetime.strptime(availability["hora_inicio"], "%H:%M").time()
        end_time = datetime.strptime(availability["hora_fin"], "%H:%M").time()
    except ValueError:
        cursor.close()
        return False, None, None, "Formato de hora de disponibilidad invalido."
    start_dt = datetime.combine(availability_date, start_time)
    end_dt = datetime.combine(availability_date, end_time)
    if end_dt <= start_dt:
        cursor.close()
        return False, None, None, "Rango horario invalido en la disponibilidad."

    if start_dt <= datetime.now():
        cursor.close()
        return False, None, None, "No se pueden asignar turnos en el pasado."

    duration_minutes = int((end_dt - start_dt).total_seconds() // 60)
    cursor.close()
    return True, start_dt, duration_minutes, ""


def create_appointment(conn: sqlite3.Connection, data: Dict) -> int:
    target_date: datetime = data["fecha"]
    is_ok, start_dt, duration, reason = _validate_slot_selection(
        conn, data["medico_id"], data["disponibilidad_id"], target_date
    )
    if not is_ok or not start_dt or duration is None:
        raise ValueError(reason)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO turnos (paciente_id, medico_id, disponibilidad_id, fecha, estado, motivo_consulta, duracion, recordatorio)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["paciente_id"],
            data["medico_id"],
            data["disponibilidad_id"],
            start_dt.isoformat(sep=" "),
            data["estado"],
            data.get("motivo_consulta"),
            duration,
            "pendiente",
        ),
    )
    cursor.execute(
        "UPDATE disponibilidad_medicos SET activa = 0 WHERE id = ?",
        (data["disponibilidad_id"],),
    )
    new_id = cursor.lastrowid
    clinical_history.upsert_from_appointment(
        conn,
        turno_id=new_id,
        paciente_id=data["paciente_id"],
        estado=data["estado"],
        fecha_turno=start_dt,
        descripcion=data.get("motivo_consulta") or "Turno creado",
        commit=False,
    )
    conn.commit()
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
        "SELECT disponibilidad_id, estado, paciente_id, fecha FROM turnos WHERE id = ?",
        (appointment_id,),
    )
    current = cursor.fetchone()
    if not current:
        cursor.close()
        return False
    disponibilidad_id = current["disponibilidad_id"]
    previous_estado = current["estado"]
    paciente_id = current["paciente_id"]
    fecha_turno = current["fecha"]

    cursor.execute(
        "UPDATE turnos SET estado = ? WHERE id = ?",
        (estado, appointment_id),
    )
    updated = cursor.rowcount > 0
    if updated and disponibilidad_id:
        if estado == "cancelado" and previous_estado != "cancelado":
            cursor.execute(
                "UPDATE disponibilidad_medicos SET activa = 1 WHERE id = ?",
                (disponibilidad_id,),
            )
        elif estado != "cancelado" and previous_estado == "cancelado":
            cursor.execute(
                "UPDATE disponibilidad_medicos SET activa = 0 WHERE id = ?",
                (disponibilidad_id,),
            )
    clinical_history.upsert_from_appointment(
        conn,
        turno_id=appointment_id,
        paciente_id=paciente_id,
        estado=estado,
        fecha_turno=fecha_turno,
        descripcion=f"Estado actualizado a {estado}",
        commit=False,
    )
    conn.commit()
    cursor.close()
    return updated


def get_appointment(conn: sqlite3.Connection, appointment_id: int) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            t.*,
            p.mail as paciente_mail,
            p.nombre as paciente_nombre,
            p.apellido as paciente_apellido,
            m.nombre as medico_nombre,
            m.apellido as medico_apellido,
            e.nombre as especialidad_nombre
        FROM turnos t
        JOIN pacientes p ON t.paciente_id = p.id
        JOIN medicos m ON t.medico_id = m.id
        JOIN especialidades e ON m.especialidad_id = e.id
        WHERE t.id = ?
        """,
        (appointment_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    return dict(row) if row else None
