def test_create_and_get_patient(client):
    payload = {
        "dni": "40111222",
        "nombre": "Test",
        "apellido": "Paciente",
        "mail": "paciente@test.com",
    }
    res = client.post("/pacientes", json=payload)
    assert res.status_code == 200
    patient_id = res.json()["id"]

    res_get = client.get(f"/pacientes/{patient_id}")
    assert res_get.status_code == 200
    data = res_get.json()
    assert data["dni"] == payload["dni"]
    assert data["nombre"] == payload["nombre"]
