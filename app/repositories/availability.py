import sqlite3
from datetime import datetime
from typing import Dict, List, Optional


def _has_overlap(
    conn: sqlite3.Connection,
    medico_id: int,
    fecha: str,
    start_str: str,
    end_str: str,
) -> bool:
    """Verifica si el rango [start, end) se superpone con otra disponibilidad del mismo medico y fecha."""
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
    if _has_overlap(
        conn,
        data["medico_id"],
        data["fecha"],
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
        (data["medico_id"], data["fecha"], data["hora_inicio"], data["hora_fin"]),
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
