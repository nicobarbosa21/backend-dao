from datetime import datetime
from typing import Dict, List

import sqlite3


def parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def appointments_by_doctor(
    conn: sqlite3.Connection, medico_id: int, start: datetime, end: datetime
) -> List[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT t.id, t.fecha, t.estado, t.motivo_consulta, t.duracion,
               p.nombre as paciente_nombre, p.apellido as paciente_apellido
        FROM turnos t
        JOIN pacientes p ON t.paciente_id = p.id
        WHERE t.medico_id = ?
          AND datetime(t.fecha) BETWEEN datetime(?) AND datetime(?)
        ORDER BY t.fecha
        """,
        (medico_id, start.isoformat(sep=" "), end.isoformat(sep=" ")),
    )
    rows = cursor.fetchall()
    cursor.close()
    return [dict(row) for row in rows]


def count_by_specialty(
    conn: sqlite3.Connection, start: datetime, end: datetime
) -> List[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT e.nombre as especialidad, COUNT(*) as cantidad
        FROM turnos t
        JOIN medicos m ON t.medico_id = m.id
        JOIN especialidades e ON m.especialidad_id = e.id
        WHERE datetime(t.fecha) BETWEEN datetime(?) AND datetime(?)
        GROUP BY e.id
        ORDER BY cantidad DESC
        """,
        (start.isoformat(sep=" "), end.isoformat(sep=" ")),
    )
    rows = cursor.fetchall()
    cursor.close()
    return [dict(row) for row in rows]


def patients_attended(
    conn: sqlite3.Connection, start: datetime, end: datetime
) -> List[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT DISTINCT p.id, p.nombre, p.apellido, p.dni, p.mail
        FROM turnos t
        JOIN pacientes p ON t.paciente_id = p.id
        WHERE t.estado = 'completado'
          AND datetime(t.fecha) BETWEEN datetime(?) AND datetime(?)
        ORDER BY p.apellido, p.nombre
        """,
        (start.isoformat(sep=" "), end.isoformat(sep=" ")),
    )
    rows = cursor.fetchall()
    cursor.close()
    return [dict(row) for row in rows]


def attendance_stats(
    conn: sqlite3.Connection, start: datetime, end: datetime
) -> Dict[str, int]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT estado, COUNT(*) as cantidad
        FROM turnos
        WHERE datetime(fecha) BETWEEN datetime(?) AND datetime(?)
        GROUP BY estado
        """,
        (start.isoformat(sep=" "), end.isoformat(sep=" ")),
    )
    rows = cursor.fetchall()
    cursor.close()
    stats = {row["estado"]: row["cantidad"] for row in rows}
    asistencia = stats.get("completado", 0)
    inasistencia = stats.get("ausente", 0) + stats.get("cancelado", 0)
    return {
        "asistencias": asistencia,
        "inasistencias": inasistencia,
        "detalle": stats,
    }
