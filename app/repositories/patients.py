import sqlite3
from typing import Dict, List, Optional


def create_patient(conn: sqlite3.Connection, data: Dict) -> int:
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO pacientes (dni, nombre, apellido, mail) VALUES (?, ?, ?, ?)",
            (data["dni"], data["nombre"], data["apellido"], data["mail"]),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        cursor.close()


def list_patients(conn: sqlite3.Connection) -> List[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pacientes ORDER BY apellido, nombre")
    rows = cursor.fetchall()
    cursor.close()
    return [dict(row) for row in rows]


def get_patient(conn: sqlite3.Connection, patient_id: int) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pacientes WHERE id = ?", (patient_id,))
    row = cursor.fetchone()
    cursor.close()
    return dict(row) if row else None


def update_patient(conn: sqlite3.Connection, patient_id: int, data: Dict) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE pacientes
        SET dni = ?, nombre = ?, apellido = ?, mail = ?
        WHERE id = ?
        """,
        (data["dni"], data["nombre"], data["apellido"], data["mail"], patient_id),
    )
    conn.commit()
    updated = cursor.rowcount > 0
    cursor.close()
    return updated


def delete_patient(conn: sqlite3.Connection, patient_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pacientes WHERE id = ?", (patient_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    cursor.close()
    return deleted
