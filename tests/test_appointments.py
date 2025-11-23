from datetime import datetime, timedelta


def _next_weekday(start: datetime, weekday: int) -> datetime:
    """Return next date (>= start) matching weekday (0=Monday)."""
    days_ahead = (weekday - start.weekday()) % 7
    return start + timedelta(days=days_ahead)


def prepare_doctor_with_availability(client, fecha_iso: str, start: str = "09:00", end: str = "12:00") -> int:
    resp = client.post(
        "/disponibilidad",
        json={
            "medico_id": 1,
            "fecha": fecha_iso,
            "hora_inicio": start,
            "hora_fin": end,
        },
    )
    assert resp.status_code == 200
    return resp.json()["id"]


def create_patient(client, dni_suffix: str = "1234") -> int:
    payload = {
        "dni": f"4000{dni_suffix}",
        "nombre": "Paciente",
        "apellido": "Prueba",
        "mail": f"paciente{dni_suffix}@test.com",
    }
    res = client.post("/pacientes", json=payload)
    assert res.status_code == 200
    return res.json()["id"]


def test_appointment_consumes_availability_and_blocks_reuse(client):
    base_date = (_next_weekday(datetime.now(), 0) + timedelta(days=14)).date()  # lunes sin seed
    availability_id = prepare_doctor_with_availability(client, base_date.isoformat())
    patient_id = create_patient(client, "1111")

    fecha_turno = base_date.isoformat()
    turno_a = {
        "paciente_id": patient_id,
        "medico_id": 1,
        "disponibilidad_id": availability_id,
        "fecha": fecha_turno,
        "motivo_consulta": "Control",
        "estado": "programado",
    }
    res = client.post("/turnos", json=turno_a)
    assert res.status_code == 200
    data = res.json()
    assert data["duracion"] == 180  # 09:00-12:00

    res_av = client.get("/disponibilidad", params={"medico_id": 1})
    slot = next(item for item in res_av.json() if item["id"] == availability_id)
    assert slot["activa"] is False

    # Intento reutilizar la misma franja sin cancelar debe fallar.
    res_b = client.post("/turnos", json=turno_a)
    assert res_b.status_code == 400
    assert "disponibilidad" in res_b.json()["detail"].lower()


def test_update_status_releases_availability_and_reports(client):
    base_date = (_next_weekday(datetime.now(), 0) + timedelta(days=14)).date()
    availability_id = prepare_doctor_with_availability(client, base_date.isoformat())
    patient_id = create_patient(client, "2222")

    fecha_turno = base_date.isoformat()
    base_turno = {
        "paciente_id": patient_id,
        "medico_id": 1,
        "disponibilidad_id": availability_id,
        "fecha": fecha_turno,
        "motivo_consulta": "Control",
        "estado": "programado",
    }
    res = client.post("/turnos", json=base_turno)
    first_turno_id = res.json()["id"]

    res_cancel = client.put(f"/turnos/{first_turno_id}/estado", json={"estado": "cancelado"})
    assert res_cancel.status_code == 200

    res_av = client.get("/disponibilidad", params={"medico_id": 1})
    slot = next(item for item in res_av.json() if item["id"] == availability_id)
    assert slot["activa"] is True

    # Reutiliza la misma disponibilidad cancelada para el mismo dia.
    res_second = client.post("/turnos", json=base_turno)
    second_turno = res_second.json()
    res_upd = client.put(
        f"/turnos/{second_turno['id']}/estado", json={"estado": "completado"}
    )
    assert res_upd.status_code == 200

    res_report = client.get(
        "/reportes/asistencias",
        params={
            "fecha_inicio": base_date.strftime("%Y-%m-%d 00:00:00"),
            "fecha_fin": (base_date + timedelta(days=1)).strftime("%Y-%m-%d 23:59:59"),
        },
    )
    assert res_report.status_code == 200
    data = res_report.json()
    assert data["asistencias"] >= 1


def test_invalid_availability_time_validation(client):
    res = client.post(
        "/disponibilidad",
        json={
            "medico_id": 1,
            "fecha": "2025-11-23",
            "hora_inicio": "21:85",
            "hora_fin": "97:75",
        },
    )
    assert res.status_code == 422
    res2 = client.post(
        "/disponibilidad",
        json={
            "medico_id": 1,
            "fecha": "2025-11-23",
            "hora_inicio": "10:00",
            "hora_fin": "09:00",
        },
    )
    assert res2.status_code == 422
