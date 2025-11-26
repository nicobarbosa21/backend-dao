import os
import sqlite3
from datetime import datetime
from typing import List, Optional
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app import schemas
from app.db import get_connection, init_db
from app.repositories import (
    appointments,
    availability,
    clinical_history,
    doctors,
    patients,
    prescriptions,
    specialties,
    admins,
)
from app.routes import history
from app.services.email_client import EmailClient
from app.services.prescription_notifier import PrescriptionNotifier
from app.services.reminder import ReminderService
from app.services import reports
from app.security import create_access_token, decode_token, verify_password

# Carga .env si esta disponible, sin forzar dependencia en entornos donde no se instalo python-dotenv.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

app = FastAPI(
    title="MediFlow API",
    version="1.1.0",
    description="Backend FastAPI + SQLite sin ORM para la gestion de turnos medicos MediFlow.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

email_client = EmailClient(
    dry_run=os.getenv("SMTP_DRY_RUN", "true").lower() == "true"
)
reminder_service = ReminderService(email_client)
prescription_notifier = PrescriptionNotifier(email_client)
bearer_scheme = HTTPBearer(auto_error=False)
app.include_router(history.router)

OPEN_PATHS = {
    "/health",
    "/auth/login",
    "/openapi.json",
    "/docs",
    "/redoc",
}


@app.middleware("http")
async def enforce_auth(request: Request, call_next):
    path = request.url.path
    if path in OPEN_PATHS or path.startswith("/docs") or path.startswith("/static"):
        return await call_next(request)

    credentials: HTTPAuthorizationCredentials = await bearer_scheme(request)
    if not credentials or credentials.scheme.lower() != "bearer":
        return JSONResponse({"detail": "No autorizado"}, status_code=401)

    token = credentials.credentials
    try:
        username = decode_token(token)
        if not username:
            raise ValueError("invalid subject")
    except Exception:
        return JSONResponse({"detail": "Token invalido o expirado"}, status_code=401)

    request.state.user = username
    return await call_next(request)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health")
def health():
    return {"status": "ok"}


# --- Autenticacion ---
@app.post("/auth/login", response_model=schemas.TokenResponse)
def login(
    payload: schemas.LoginRequest, conn: sqlite3.Connection = Depends(get_connection)
):
    admin = admins.get_admin_by_username(conn, payload.username)
    if not admin or not verify_password(payload.password, admin["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciales invalidas")
    token = create_access_token(payload.username)
    return {"access_token": token, "token_type": "bearer"}


# --- Pacientes ---
@app.post("/pacientes", response_model=schemas.Patient)
def create_patient(
    payload: schemas.PatientCreate, conn: sqlite3.Connection = Depends(get_connection)
):
    try:
        new_id = patients.create_patient(conn, payload.dict())
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="DNI o mail ya registrado.")
    return {"id": new_id, **payload.dict()}


@app.get("/pacientes", response_model=List[schemas.Patient])
def list_all_patients(conn: sqlite3.Connection = Depends(get_connection)):
    return patients.list_patients(conn)


@app.get("/pacientes/{patient_id}", response_model=schemas.Patient)
def get_patient(patient_id: int, conn: sqlite3.Connection = Depends(get_connection)):
    patient = patients.get_patient(conn, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Paciente no encontrado.")
    return patient


@app.put("/pacientes/{patient_id}", response_model=schemas.Patient)
def update_patient(
    patient_id: int,
    payload: schemas.PatientCreate,
    conn: sqlite3.Connection = Depends(get_connection),
):
    ok = patients.update_patient(conn, patient_id, payload.dict())
    if not ok:
        raise HTTPException(status_code=404, detail="Paciente no encontrado.")
    return {"id": patient_id, **payload.dict()}


@app.delete("/pacientes/{patient_id}")
def delete_patient(patient_id: int, conn: sqlite3.Connection = Depends(get_connection)):
    ok = patients.delete_patient(conn, patient_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Paciente no encontrado.")
    return {"deleted": True}


# --- Especialidades ---
@app.post("/especialidades", response_model=schemas.Specialty)
def create_specialty(
    payload: schemas.SpecialtyCreate, conn: sqlite3.Connection = Depends(get_connection)
):
    new_id = specialties.create_specialty(conn, payload.dict())
    return {"id": new_id, **payload.dict()}


@app.get("/especialidades", response_model=List[schemas.Specialty])
def list_specialties(conn: sqlite3.Connection = Depends(get_connection)):
    return specialties.list_specialties(conn)


@app.put("/especialidades/{specialty_id}", response_model=schemas.Specialty)
def update_specialty(
    specialty_id: int,
    payload: schemas.SpecialtyCreate,
    conn: sqlite3.Connection = Depends(get_connection),
):
    ok = specialties.update_specialty(conn, specialty_id, payload.dict())
    if not ok:
        raise HTTPException(status_code=404, detail="Especialidad no encontrada.")
    return {"id": specialty_id, **payload.dict()}


@app.delete("/especialidades/{specialty_id}")
def delete_specialty(
    specialty_id: int, conn: sqlite3.Connection = Depends(get_connection)
):
    ok = specialties.delete_specialty(conn, specialty_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Especialidad no encontrada.")
    return {"deleted": True}


# --- Médicos ---
@app.post("/medicos", response_model=schemas.Doctor)
def create_doctor(
    payload: schemas.DoctorCreate, conn: sqlite3.Connection = Depends(get_connection)
):
    new_id = doctors.create_doctor(conn, payload.dict())
    return {"id": new_id, **payload.dict()}


@app.get("/medicos", response_model=List[schemas.Doctor])
def list_doctors(conn: sqlite3.Connection = Depends(get_connection)):
    return doctors.list_doctors(conn)


@app.get("/medicos/{doctor_id}", response_model=schemas.Doctor)
def get_doctor(doctor_id: int, conn: sqlite3.Connection = Depends(get_connection)):
    doctor = doctors.get_doctor(conn, doctor_id)
    if not doctor:
        raise HTTPException(status_code=404, detail="Médico no encontrado.")
    return doctor


@app.put("/medicos/{doctor_id}", response_model=schemas.Doctor)
def update_doctor(
    doctor_id: int,
    payload: schemas.DoctorCreate,
    conn: sqlite3.Connection = Depends(get_connection),
):
    ok = doctors.update_doctor(conn, doctor_id, payload.dict())
    if not ok:
        raise HTTPException(status_code=404, detail="Médico no encontrado.")
    return {"id": doctor_id, **payload.dict()}


@app.delete("/medicos/{doctor_id}")
def delete_doctor(doctor_id: int, conn: sqlite3.Connection = Depends(get_connection)):
    ok = doctors.delete_doctor(conn, doctor_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Médico no encontrado.")
    return {"deleted": True}


# --- Disponibilidad horaria ---
@app.post("/disponibilidad", response_model=schemas.Availability)
def create_availability(
    payload: schemas.AvailabilityCreate, conn: sqlite3.Connection = Depends(get_connection)
):
    try:
        new_id = availability.create_availability(conn, payload.dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": new_id, **payload.dict()}


@app.get("/disponibilidad", response_model=List[schemas.Availability])
def list_availability(
    medico_id: Optional[int] = None, conn: sqlite3.Connection = Depends(get_connection)
):
    return availability.list_availability(conn, medico_id)


@app.delete("/disponibilidad/{availability_id}")
def delete_availability(
    availability_id: int, conn: sqlite3.Connection = Depends(get_connection)
):
    ok = availability.delete_availability(conn, availability_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Disponibilidad no encontrada.")
    return {"deleted": True}


# --- Turnos ---
@app.post("/turnos", response_model=schemas.Appointment)
def create_appointment(
    payload: schemas.AppointmentCreate,
    background_tasks: BackgroundTasks,
    conn: sqlite3.Connection = Depends(get_connection),
):
    try:
        new_id = appointments.create_appointment(conn, payload.dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="Paciente o médico inexistente.")

    turno = appointments.get_appointment(conn, new_id)
    appointment_dt = datetime.fromisoformat(turno["fecha"])
    patient_full_name = f"{turno['paciente_nombre']} {turno['paciente_apellido']}"
    doctor_full_name = f"{turno['medico_nombre']} {turno['medico_apellido']}"
    specialty_name = turno["especialidad_nombre"]
    # Desacoplar envío usando BackgroundTasks.
    background_tasks.add_task(
        reminder_service.schedule_reminders,
        appointment_dt,
        patient_full_name,
        turno["paciente_mail"],
        doctor_full_name,
        specialty_name,
    )
    return {**turno}


@app.get("/turnos", response_model=List[schemas.Appointment])
def list_all_appointments(
    medico_id: Optional[int] = None, conn: sqlite3.Connection = Depends(get_connection)
):
    return appointments.list_appointments(conn, medico_id)


@app.put("/turnos/{appointment_id}/estado")
def update_appointment_status(
    appointment_id: int,
    payload: schemas.AppointmentUpdateStatus,
    conn: sqlite3.Connection = Depends(get_connection),
):
    ok = appointments.update_status(conn, appointment_id, payload.estado)
    if not ok:
        raise HTTPException(status_code=404, detail="Turno no encontrado.")
    return {"id": appointment_id, "estado": payload.estado}


# --- Historial clínico ---
@app.post("/historial", response_model=schemas.ClinicalRecord)
def create_record(
    payload: schemas.ClinicalRecordCreate,
    conn: sqlite3.Connection = Depends(get_connection),
):
    new_id = clinical_history.add_record(conn, payload.dict())
    return {"id": new_id, **payload.dict()}


@app.get("/pacientes/{patient_id}/historial", response_model=List[schemas.ClinicalRecord])
def list_history(
    patient_id: int, conn: sqlite3.Connection = Depends(get_connection)
):
    return clinical_history.list_records(conn, patient_id)


# --- Recetas ---
@app.get("/recetas", response_model=List[schemas.Prescription])
def list_all_prescriptions(conn: sqlite3.Connection = Depends(get_connection)):
    return prescriptions.list_all_prescriptions(conn)


@app.get("/recetas/{prescription_id}", response_model=schemas.Prescription)
def get_prescription(
    prescription_id: int, conn: sqlite3.Connection = Depends(get_connection)
):
    prescription = prescriptions.get_prescription(conn, prescription_id)
    if not prescription:
        raise HTTPException(status_code=404, detail="Receta no encontrada.")
    return prescription


@app.post("/recetas", response_model=schemas.Prescription)
def create_prescription(
    payload: schemas.PrescriptionCreate,
    background_tasks: BackgroundTasks,
    conn: sqlite3.Connection = Depends(get_connection),
):
    patient = patients.get_patient(conn, payload.paciente_id)
    doctor = doctors.get_doctor(conn, payload.medico_id)
    if not patient or not doctor:
        raise HTTPException(status_code=404, detail="Paciente o medico no encontrado.")

    new_id = prescriptions.create_prescription(conn, payload.dict())
    patient_name = f"{patient['nombre']} {patient['apellido']}"
    doctor_name = f"{doctor['nombre']} {doctor['apellido']}"
    background_tasks.add_task(
        prescription_notifier.notify_prescription,
        patient_name,
        patient["mail"],
        doctor_name,
        payload.descripcion,
    )
    return {"id": new_id, **payload.dict()}


@app.delete("/recetas/{prescription_id}")
def delete_prescription(
    prescription_id: int, conn: sqlite3.Connection = Depends(get_connection)
):
    deleted = prescriptions.delete_prescription(conn, prescription_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Receta no encontrada.")
    return {"deleted": True}


@app.get("/pacientes/{patient_id}/recetas", response_model=List[schemas.Prescription])
def list_prescriptions(
    patient_id: int, conn: sqlite3.Connection = Depends(get_connection)
):
    return prescriptions.list_prescriptions(conn, patient_id)


# --- Reportes ---
@app.get("/reportes/turnos-medico")
def report_appointments_by_doctor(
    medico_id: int,
    fecha_inicio: datetime,
    fecha_fin: datetime,
    conn: sqlite3.Connection = Depends(get_connection),
):
    data = reports.appointments_by_doctor(conn, medico_id, fecha_inicio, fecha_fin)
    return {"items": data, "total": len(data)}


@app.get("/reportes/turnos-por-especialidad")
def report_count_by_specialty(
    conn: sqlite3.Connection = Depends(get_connection),
):
    data = reports.count_by_specialty(conn)
    return {"items": data}


@app.get("/reportes/pacientes-atendidos")
def report_patients_attended(
    fecha_inicio: datetime,
    fecha_fin: datetime,
    conn: sqlite3.Connection = Depends(get_connection),
):
    data = reports.patients_attended(conn, fecha_inicio, fecha_fin)
    return {"items": data, "total": len(data)}


@app.get("/reportes/asistencias")
def report_attendance_stats(
    fecha_inicio: datetime,
    fecha_fin: datetime,
    conn: sqlite3.Connection = Depends(get_connection),
):
    return reports.attendance_stats(conn, fecha_inicio, fecha_fin)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
