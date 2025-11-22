import sqlite3
from typing import Dict, List, Optional


def create_availability(conn: sqlite3.Connection, data: Dict) -> int:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO disponibilidad_medicos (medico_id, dia_semana, hora_inicio, hora_fin)
        VALUES (?, ?, ?, ?)
        """,
        (data["medico_id"], data["dia_semana"], data["hora_inicio"], data["hora_fin"]),
    )
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    return new_id


def list_availability(conn: sqlite3.Connection, medico_id: Optional[int] = None) -> List[dict]:
    cursor = conn.cursor()
    if medico_id:
        cursor.execute(
            "SELECT * FROM disponibilidad_medicos WHERE medico_id = ? ORDER BY dia_semana, hora_inicio",
            (medico_id,),
        )
    else:
        cursor.execute(
            "SELECT * FROM disponibilidad_medicos ORDER BY medico_id, dia_semana, hora_inicio"
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
