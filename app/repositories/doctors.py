import sqlite3
from typing import Dict, List, Optional


def create_doctor(conn: sqlite3.Connection, data: Dict) -> int:
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO medicos (nombre, apellido, especialidad_id, mail)
        VALUES (?, ?, ?, ?)
        """,
        (data["nombre"], data["apellido"], data["especialidad_id"], data["mail"]),
    )
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    return new_id


def list_doctors(conn: sqlite3.Connection) -> List[dict]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT m.*, e.nombre as especialidad
        FROM medicos m
        JOIN especialidades e ON m.especialidad_id = e.id
        ORDER BY m.apellido, m.nombre
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    return [dict(row) for row in rows]


def get_doctor(conn: sqlite3.Connection, doctor_id: int) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM medicos WHERE id = ?", (doctor_id,))
    row = cursor.fetchone()
    cursor.close()
    return dict(row) if row else None


def update_doctor(conn: sqlite3.Connection, doctor_id: int, data: Dict) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE medicos
        SET nombre = ?, apellido = ?, especialidad_id = ?, mail = ?
        WHERE id = ?
        """,
        (
            data["nombre"],
            data["apellido"],
            data["especialidad_id"],
            data["mail"],
            doctor_id,
        ),
    )
    conn.commit()
    updated = cursor.rowcount > 0
    cursor.close()
    return updated


def delete_doctor(conn: sqlite3.Connection, doctor_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM medicos WHERE id = ?", (doctor_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    cursor.close()
    return deleted
