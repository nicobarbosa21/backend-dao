import sqlite3
from typing import List

from fastapi import APIRouter, Depends

from app.db import get_connection
from app.repositories import clinical_history
from app import schemas

router = APIRouter()


@router.get("/historial", response_model=List[schemas.ClinicalRecord])
def list_all_history(conn: sqlite3.Connection = Depends(get_connection)):
    return clinical_history.list_records(conn, paciente_id=None)
