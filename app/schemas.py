from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, validator


class PatientCreate(BaseModel):
    dni: str = Field(..., min_length=6)
    nombre: str
    apellido: str
    mail: EmailStr


class Patient(PatientCreate):
    id: int


class SpecialtyCreate(BaseModel):
    nombre: str


class Specialty(SpecialtyCreate):
    id: int


class DoctorCreate(BaseModel):
    nombre: str
    apellido: str
    especialidad_id: int
    mail: EmailStr


class Doctor(DoctorCreate):
    id: int


class AvailabilityCreate(BaseModel):
    medico_id: int
    fecha: date
    hora_inicio: str = Field(..., regex=r"^\d{2}:\d{2}$")
    hora_fin: str = Field(..., regex=r"^\d{2}:\d{2}$")

    @validator("hora_inicio")
    def validate_hora_inicio(cls, v):
        try:
            datetime.strptime(v, "%H:%M").time()
        except ValueError:
            raise ValueError("hora_inicio debe estar entre 00:00 y 23:59 (HH:MM)")
        return v

    @validator("hora_fin")
    def validate_range(cls, v, values):
        start = values.get("hora_inicio")
        try:
            end_time = datetime.strptime(v, "%H:%M").time()
            start_time = datetime.strptime(start, "%H:%M").time() if start else None
        except ValueError:
            raise ValueError("hora_fin debe estar entre 00:00 y 23:59 (HH:MM)")

        if start_time and end_time <= start_time:
            raise ValueError("hora_fin debe ser mayor que hora_inicio")
        return v


class Availability(AvailabilityCreate):
    id: int
    activa: bool = True


class AppointmentCreate(BaseModel):
    paciente_id: int
    medico_id: int
    disponibilidad_id: int
    fecha: datetime
    motivo_consulta: Optional[str] = None
    estado: str = Field(default="programado")

    @validator("fecha", pre=True)
    def normalize_fecha(cls, v):
        if isinstance(v, str) and len(v) == 10:
            return f"{v} 00:00:00"
        return v

    @validator("estado")
    def validate_estado(cls, v):
        allowed = {"programado", "completado", "cancelado", "ausente"}
        if v not in allowed:
            raise ValueError(f"Estado invalido. Valores permitidos: {allowed}")
        return v


class Appointment(AppointmentCreate):
    id: int
    duracion: int


class AppointmentUpdateStatus(BaseModel):
    estado: str

    @validator("estado")
    def validate_estado(cls, v):
        allowed = {"programado", "completado", "cancelado", "ausente"}
        if v not in allowed:
            raise ValueError(f"Estado invalido. Valores permitidos: {allowed}")
        return v


class ClinicalRecordCreate(BaseModel):
    paciente_id: int
    turno_id: Optional[int] = None
    descripcion: str


class ClinicalRecord(ClinicalRecordCreate):
    id: int


class PrescriptionCreate(BaseModel):
    medico_id: int
    paciente_id: int
    descripcion: str


class Prescription(PrescriptionCreate):
    id: int


class ReportRequest(BaseModel):
    fecha_inicio: datetime
    fecha_fin: datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
