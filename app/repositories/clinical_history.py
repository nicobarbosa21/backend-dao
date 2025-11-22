import sqlite3
from typing import Dict, List


def add_record(conn: sqlite3.Connection, data: Dict) -> int:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO historial_clinico (paciente_id, turno_id, descripcion)
        VALUES (?, ?, ?)
        """,
        (data["paciente_id"], data.get("turno_id"), data["descripcion"]),
    )
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    return new_id


def list_records(conn: sqlite3.Connection, paciente_id: int) -> List[dict]:
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM historial_clinico WHERE paciente_id = ? ORDER BY id DESC",
        (paciente_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    return [dict(row) for row in rows]
