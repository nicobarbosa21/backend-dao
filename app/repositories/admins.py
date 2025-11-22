import sqlite3
from typing import Dict, Optional


def get_admin_by_username(conn: sqlite3.Connection, username: str) -> Optional[dict]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admins WHERE username = ?", (username,))
    row = cursor.fetchone()
    cursor.close()
    return dict(row) if row else None


def create_admin(conn: sqlite3.Connection, data: Dict) -> int:
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
        (data["username"], data["password_hash"]),
    )
    conn.commit()
    new_id = cursor.lastrowid
    cursor.close()
    return new_id
