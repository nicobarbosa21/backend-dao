from datetime import datetime


def prepare_doctor_with_availability(client):
    # Usa doctor semilla (id=1) y carga disponibilidad lunes.
    resp = client.post(
        "/disponibilidad",
        json={
            "medico_id": 1,
            "dia_semana": 0,
            "hora_inicio": "09:00",
            "hora_fin": "12:00",
        },
    )
    assert resp.status_code == 200


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


def test_appointment_respects_availability_and_blocks_overlap(client):
    prepare_doctor_with_availability(client)
    patient_id = create_patient(client, "1111")

    turno_a = {
        "paciente_id": patient_id,
        "medico_id": 1,
        "fecha": "2025-01-06 10:00:00",
        "duracion": 30,
        "motivo_consulta": "Control",
        "estado": "programado",
    }
    res = client.post("/turnos", json=turno_a)
    assert res.status_code == 200

    # Intento solapado debe fallar.
    turno_b = turno_a.copy()
    turno_b["fecha"] = "2025-01-06 10:15:00"
    res_b = client.post("/turnos", json=turno_b)
    assert res_b.status_code == 400
    assert "solapado" in res_b.json()["detail"].lower() or "turno" in res_b.json()["detail"].lower()


def test_update_status_and_reports(client):
    prepare_doctor_with_availability(client)
    patient_id = create_patient(client, "2222")

    base_turno = {
        "paciente_id": patient_id,
        "medico_id": 1,
        "fecha": "2025-01-06 11:00:00",
        "duracion": 30,
        "motivo_consulta": "Control",
        "estado": "programado",
    }
    res = client.post("/turnos", json=base_turno)
    turno_id = res.json()["id"]

    # Marcar como completado.
    res_upd = client.put(f"/turnos/{turno_id}/estado", json={"estado": "completado"})
    assert res_upd.status_code == 200

    # Reporte de asistencia.
    res_report = client.get(
        "/reportes/asistencias",
        params={
            "fecha_inicio": "2025-01-01 00:00:00",
            "fecha_fin": "2025-01-31 23:59:59",
        },
    )
    assert res_report.status_code == 200
    data = res_report.json()
    assert data["asistencias"] >= 1
