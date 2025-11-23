import sqlite3
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional


def _next_weekday(start: date, weekday: int) -> date:
    days_ahead = (weekday - start.weekday()) % 7
    return start + timedelta(days=days_ahead)


def _ensure_fecha_column(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(disponibilidad_medicos)")
    cols = [row["name"] for row in cursor.fetchall()]
    if "fecha" in cols:
        cursor.close()
        return
    cursor.execute("ALTER TABLE disponibilidad_medicos ADD COLUMN fecha TEXT")
    conn.commit()
    cursor.execute("SELECT id, dia_semana FROM disponibilidad_medicos")
    rows = cursor.fetchall()
    today = date.today()
    for row in rows:
        dia = row["dia_semana"]
        if dia is None:
            continue
        target = _next_weekday(today, int(dia))
        cursor.execute(
            "UPDATE disponibilidad_medicos SET fecha = ? WHERE id = ?",
            (target.isoformat(), row["id"]),
        )
    conn.commit()
    cursor.close()


def _has_overlap(
    conn: sqlite3.Connection,
    medico_id: int,
    fecha: str,
    start_str: str,
    end_str: str,
) -> bool:
    """Verifica si el rango [start, end) se superpone con otra disponibilidad del mismo medico y fecha."""
    _ensure_fecha_column(conn)
    try:
        new_start = datetime.strptime(start_str, "%H:%M").time()
        new_end = datetime.strptime(end_str, "%H:%M").time()
    except ValueError:
        raise ValueError("Formato de hora invalido, use HH:MM.")

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT hora_inicio, hora_fin
        FROM disponibilidad_medicos
        WHERE medico_id = ? AND fecha = ?
        """,
        (medico_id, fecha),
    )
    rows = cursor.fetchall()
    cursor.close()

    for row in rows:
        try:
            existing_start = datetime.strptime(row["hora_inicio"], "%H:%M").time()
            existing_end = datetime.strptime(row["hora_fin"], "%H:%M").time()
        except ValueError:
            # Si hay datos corruptos, prevenir crear otra franja solapada.
            return True
        # Solapa si start < other_end y end > other_start
        if new_start < existing_end and new_end > existing_start:
            return True
    return False


def create_availability(conn: sqlite3.Connection, data: Dict) -> int:
    _ensure_fecha_column(conn)
    fecha = data["fecha"]
    if isinstance(fecha, date):
        fecha = fecha.isoformat()

    if _has_overlap(
        conn,
        data["medico_id"],
        fecha,
        data["hora_inicio"],
        data["hora_fin"],
    ):
        raise ValueError("La disponibilidad se superpone con otra ya registrada para ese medico y fecha.")

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO disponibilidad_medicos (medico_id, fecha, hora_inicio, hora_fin)
        VALUES (?, ?, ?, ?)
        """,
        (data["medico_id"], fecha, data["hora_inicio"], data["hora_fin"]),
    )
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    return new_id


def list_availability(conn: sqlite3.Connection, medico_id: Optional[int] = None) -> List[dict]:
    cursor = conn.cursor()
    if medico_id:
        cursor.execute(
            "SELECT * FROM disponibilidad_medicos WHERE medico_id = ? ORDER BY fecha, hora_inicio",
            (medico_id,),
        )
    else:
        cursor.execute(
            "SELECT * FROM disponibilidad_medicos ORDER BY medico_id, fecha, hora_inicio"
        )
    rows = cursor.fetchall()
    cursor.close()
    return [dict(row) for row in rows]


def delete_availability(conn: sqlite3.Connection, availability_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM disponibilidad_medicos WHERE id = ?", (availability_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    cursor.close()
    return deleted


def get_availability(conn: sqlite3.Connection, availability_id: int) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM disponibilidad_medicos WHERE id = ?",
        (availability_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    return dict(row) if row else None


def set_active(conn: sqlite3.Connection, availability_id: int, activa: bool) -> None:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE disponibilidad_medicos SET activa = ? WHERE id = ?",
        (1 if activa else 0, availability_id),
    )
    conn.commit()
    cursor.close()
