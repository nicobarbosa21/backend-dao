import os
import pytest
from fastapi.testclient import TestClient

from app.db import Database, init_db
from app.main import app


@pytest.fixture(autouse=True)
def setup_db(tmp_path):
    db_path = tmp_path / "test.db"
    os.environ["ADMIN_DEFAULT_PASSWORD"] = "admin123"
    os.environ["DATABASE_URL"] = str(db_path)
    Database.reset_instance(str(db_path))
    init_db()
    yield
    Database.reset_instance(None)


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        login = test_client.post(
            "/auth/login",
            json={"username": "admin", "password": os.getenv("ADMIN_DEFAULT_PASSWORD", "admin123")},
        )
        token = login.json()["access_token"]
        test_client.headers.update({"Authorization": f"Bearer {token}"})
        yield test_client
