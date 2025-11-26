from datetime import date, datetime, timedelta
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, validator


class PatientCreate(BaseModel):
    dni: str = Field(..., min_length=6)
    nombre: str
    apellido: str
    mail: str

    @validator("mail")
    def validate_mail(cls, v: str):
        # Validar formato basico sin bloquear datos historicos en responses.
        if "@" not in v or v.startswith("@") or v.endswith("@"):
            raise ValueError("mail debe tener formato de email")
        return v


class Patient(BaseModel):
    id: int
    dni: str
    nombre: str
    apellido: str
    mail: str


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
    fecha: Optional[date] = None
    dia_semana: Optional[int] = Field(None, ge=0, le=6, description="0=lunes, 6=domingo (legado)")
    hora_inicio: str = Field(..., regex=r"^\d{2}:\d{2}$")
    hora_fin: str = Field(..., regex=r"^\d{2}:\d{2}$")

    @validator("fecha", always=True)
    def ensure_fecha(cls, v, values):
        if v:
            return v
        dia = values.get("dia_semana")
        if dia is None:
            raise ValueError("Debe enviar fecha o dia_semana")
        today = date.today()
        days_ahead = (dia - today.weekday()) % 7
        return today + timedelta(days=days_ahead)

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
    disponibilidad_id: Optional[int] = None
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
    estado: str = "programado"
    fecha_turno: Optional[datetime] = None

    @validator("estado")
    def validate_estado(cls, v):
        allowed = {"programado", "completado", "cancelado", "ausente"}
        if v not in allowed:
            raise ValueError(f"Estado invalido. Valores permitidos: {allowed}")
        return v

    @validator("fecha_turno", pre=True)
    def normalize_fecha_turno(cls, v):
        if isinstance(v, str) and len(v) == 10:
            return f"{v} 00:00:00"
        return v


class ClinicalRecord(ClinicalRecordCreate):
    id: int
    medico_nombre: Optional[str] = None
    medico_apellido: Optional[str] = None
    especialidad: Optional[str] = None


class PrescriptionCreate(BaseModel):
    medico_id: int
    paciente_id: int
    descripcion: str
    medico_nombre: str
    medico_apellido: str


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
