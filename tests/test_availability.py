def test_reject_overlapping_slots_for_same_doctor(client):
    base_payload = {
        "medico_id": 1,
        "fecha": "2025-11-23",
        "hora_inicio": "14:00",
        "hora_fin": "15:00",
    }
    res1 = client.post("/disponibilidad", json=base_payload)
    assert res1.status_code == 200

    overlap = {**base_payload, "hora_inicio": "14:30", "hora_fin": "15:30"}
    res2 = client.post("/disponibilidad", json=overlap)
    assert res2.status_code == 400
    assert "superpone" in res2.json()["detail"].lower()

    contigua = {**base_payload, "hora_inicio": "15:00", "hora_fin": "16:00"}
    res3 = client.post("/disponibilidad", json=contigua)
    assert res3.status_code == 200


def test_same_slot_allowed_for_different_doctors(client):
    payload = {
        "medico_id": 1,
        "fecha": "2025-12-01",
        "hora_inicio": "09:00",
        "hora_fin": "10:00",
    }
    res1 = client.post("/disponibilidad", json=payload)
    assert res1.status_code == 200

    payload_other = {**payload, "medico_id": 2}
    res2 = client.post("/disponibilidad", json=payload_other)
    assert res2.status_code == 200


def test_availability_response_without_dia_semana(client):
    payload = {
        "medico_id": 1,
        "fecha": "2025-12-15",
        "hora_inicio": "11:00",
        "hora_fin": "12:00",
    }
    res = client.post("/disponibilidad", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "dia_semana" not in data

    res_list = client.get("/disponibilidad", params={"medico_id": payload["medico_id"]})
    assert res_list.status_code == 200
    assert all("dia_semana" not in item for item in res_list.json())


def test_availability_requires_fecha(client):
    res = client.post(
        "/disponibilidad",
        json={"medico_id": 1, "hora_inicio": "10:00", "hora_fin": "11:00"},
    )
    assert res.status_code == 422
