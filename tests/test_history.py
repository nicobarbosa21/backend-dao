from datetime import datetime, timedelta


def _next_weekday(start: datetime, weekday: int) -> datetime:
    days_ahead = (weekday - start.weekday()) % 7
    return start + timedelta(days=days_ahead)


def _create_availability(client, medico_id: int, fecha_iso: str) -> int:
    res = client.post(
        "/disponibilidad",
        json={
            "medico_id": medico_id,
            "fecha": fecha_iso,
            "hora_inicio": "09:00",
            "hora_fin": "11:00",
        },
    )
    assert res.status_code == 200
    return res.json()["id"]


def _create_patient(client) -> int:
    payload = {
        "dni": "50123456",
        "nombre": "Historial",
        "apellido": "Prueba",
        "mail": "historial@test.com",
    }
    res = client.post("/pacientes", json=payload)
    assert res.status_code == 200
    return res.json()["id"]


def test_history_tracks_appointment_creation_and_updates(client):
    base_date = (_next_weekday(datetime.now(), 0) + timedelta(days=28)).date()
    availability_id = _create_availability(client, 1, base_date.isoformat())
    patient_id = _create_patient(client)

    res_turno = client.post(
        "/turnos",
        json={
            "paciente_id": patient_id,
            "medico_id": 1,
            "disponibilidad_id": availability_id,
            "fecha": base_date.isoformat(),
            "motivo_consulta": "Chequeo general",
            "estado": "programado",
        },
    )
    assert res_turno.status_code == 200
    turno_id = res_turno.json()["id"]

    res_hist = client.get(f"/pacientes/{patient_id}/historial")
    assert res_hist.status_code == 200
    historial = res_hist.json()
    entry = next(item for item in historial if item["turno_id"] == turno_id)
    assert entry["estado"] == "programado"
    assert entry["fecha_turno"] is not None

    res_update = client.put(
        f"/turnos/{turno_id}/estado",
        json={"estado": "completado"},
    )
    assert res_update.status_code == 200

    res_hist_after = client.get(f"/pacientes/{patient_id}/historial")
    assert res_hist_after.status_code == 200
    updated_entry = next(item for item in res_hist_after.json() if item["turno_id"] == turno_id)
    assert updated_entry["estado"] == "completado"
