def test_login_returns_token(client):
    res = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data and data["token_type"] == "bearer"


def test_protected_endpoint_requires_token():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as unauth_client:
        res = unauth_client.get("/pacientes")
        assert res.status_code == 401
        assert "No autorizado" in res.json()["detail"]


def test_login_rejects_bad_credentials(client):
    res = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert res.status_code == 401
    assert "Credenciales" in res.json()["detail"]
