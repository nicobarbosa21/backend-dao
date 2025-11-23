def test_reject_overlapping_slots_for_same_doctor(client):
    base_payload = {
        "medico_id": 1,
        "fecha": "2025-11-23",
        "hora_inicio": "14:00",
        "hora_fin": "15:00",
    }
    res1 = client.post("/disponibilidad", json=base_payload)
    assert res1.status_code == 200

    # Solapa (14:30-15:30) mismo medico y fecha -> 400
    overlap = {**base_payload, "hora_inicio": "14:30", "hora_fin": "15:30"}
    res2 = client.post("/disponibilidad", json=overlap)
    assert res2.status_code == 400
    assert "superpone" in res2.json()["detail"].lower()

    # Otra franja contigua (15:00-16:00) debe permitirse
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
