import sqlite3
from typing import Dict, List, Optional


def create_specialty(conn: sqlite3.Connection, data: Dict) -> int:
    cursor = conn.cursor()
    cursor.execute("INSERT INTO especialidades (nombre) VALUES (?)", (data["nombre"],))
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    return new_id


def list_specialties(conn: sqlite3.Connection) -> List[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM especialidades ORDER BY nombre")
    rows = cursor.fetchall()
    cursor.close()
    return [dict(row) for row in rows]


def get_specialty(conn: sqlite3.Connection, specialty_id: int) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM especialidades WHERE id = ?", (specialty_id,))
    row = cursor.fetchone()
    cursor.close()
    return dict(row) if row else None


def update_specialty(conn: sqlite3.Connection, specialty_id: int, data: Dict) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE especialidades SET nombre = ? WHERE id = ?",
        (data["nombre"], specialty_id),
    )
    conn.commit()
    updated = cursor.rowcount > 0
    cursor.close()
    return updated


def delete_specialty(conn: sqlite3.Connection, specialty_id: int) -> bool:
    cursor = conn.cursor()
    cursor.execute("DELETE FROM especialidades WHERE id = ?", (specialty_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    cursor.close()
    return deleted
