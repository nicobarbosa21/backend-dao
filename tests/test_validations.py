import pytest


def patient_payload(**overrides):
    base = {
        "dni": "50111222",
        "nombre": "Maria",
        "apellido": "Prueba",
        "mail": "maria.prueba@test.com",
    }
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    "field,value",
    [
        ("nombre", "Juan3"),
        ("apellido", "Perez!"),
    ],
)
def test_patient_rejects_non_letter_fields(client, field, value):
    res = client.post("/pacientes", json=patient_payload(**{field: value}))
    assert res.status_code == 422
    messages = [err["msg"] for err in res.json().get("detail", [])]
    assert any("solo puede contener letras" in msg for msg in messages)


def test_patient_rejects_name_length_over_limit(client):
    res = client.post("/pacientes", json=patient_payload(nombre="A" * 21))
    assert res.status_code == 422
    messages = [err["msg"] for err in res.json().get("detail", [])]
    assert any("entre 1 y 20" in msg for msg in messages)


def test_patient_accepts_boundary_lengths(client):
    payload = patient_payload(
        dni="60999888",
        nombre="A",
        apellido="B" * 20,
        mail="borde@test.com",
    )
    res = client.post("/pacientes", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["nombre"] == "A"
    assert data["apellido"] == "B" * 20


@pytest.mark.parametrize(
    "nombre",
    [
        "Cardio123",
        "Especialidad!",
        "NombreDemasiadoLargoParaValidacion",
    ],
)
def test_specialty_rejects_invalid_names(client, nombre):
    res = client.post("/especialidades", json={"nombre": nombre})
    assert res.status_code == 422


@pytest.mark.parametrize(
    "override",
    [
        {"nombre": "Doc1"},
        {"apellido": "Prueba#"},
        {"nombre": "A" * 21},
        {"apellido": "B" * 21},
    ],
)
def test_doctor_name_validation(client, override):
    payload = {
        "nombre": "Laura",
        "apellido": "Prueba",
        "especialidad_id": 1,
        "mail": "nuevo.doctor@test.com",
    }
    payload.update(override)
    res = client.post("/medicos", json=payload)
    assert res.status_code == 422
