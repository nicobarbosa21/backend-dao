import os
import pytest
from fastapi.testclient import TestClient

from app.db import Database, init_db
from app.main import app


@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    # Base SQLite aislada por test.
    db_path = tmp_path / "test.db"
    os.environ["DATABASE_URL"] = str(db_path)
    Database.reset_instance(str(db_path))
    init_db()
    yield
    Database.reset_instance(None)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
