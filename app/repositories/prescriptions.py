import sqlite3
from typing import Dict, List


def create_prescription(conn: sqlite3.Connection, data: Dict) -> int:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO recetas (medico_id, paciente_id, descripcion)
        VALUES (?, ?, ?)
        """,
        (data["medico_id"], data["paciente_id"], data["descripcion"]),
    )
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    return new_id


def list_prescriptions(conn: sqlite3.Connection, paciente_id: int) -> List[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT r.*, m.nombre as medico_nombre, m.apellido as medico_apellido
        FROM recetas r
        JOIN medicos m ON r.medico_id = m.id
        WHERE r.paciente_id = ?
        ORDER BY r.id DESC
        """,
        (paciente_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    return [dict(row) for row in rows]
