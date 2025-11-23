import threading
from datetime import datetime, timedelta
from typing import Iterable, List

from app.observers.base import Observer, Subject
from app.services.email_client import EmailClient


class PatientObserver(Observer):
    def __init__(self, name: str, email: str, email_client: EmailClient) -> None:
        self.name = name
        self.email = email
        self.email_client = email_client

    def update(self, data: str) -> None:
        subject = "Recordatorio de turno medico"
        self.email_client.send_email(self.email, subject, data)


class ReminderSubject(Subject):
    def __init__(self) -> None:
        super().__init__()


class ReminderService:
    def __init__(
        self,
        email_client: EmailClient,
        lead_times: Iterable[timedelta] = (
            timedelta(days=1),
            timedelta(hours=6),
            timedelta(hours=1),
        ),
    ) -> None:
        self.email_client = email_client
        self.lead_times: List[timedelta] = list(lead_times)

    def schedule_reminders(
        self,
        appointment_dt: datetime,
        patient_name: str,
        patient_email: str,
        doctor_name: str,
        specialty: str,
    ) -> List[threading.Timer]:
        subject = ReminderSubject()
        subject.attach(PatientObserver(patient_name, patient_email, self.email_client))

        date_str = appointment_dt.strftime("%Y-%m-%d")
        time_str = appointment_dt.strftime("%H:%M")
        confirmation_msg = (
            f"Confirmamos su reserva del turno con {doctor_name} de {specialty} el {date_str} a las {time_str}.\n"
            "Lo esperamos!\nConsultorio Médico Privado - Chacabuco 1244, Nueva Córdoba, Córdoba."
        )
        subject.notify(f"Hola {patient_name},\n\n{confirmation_msg}")

        timers: List[threading.Timer] = []
        now = datetime.now()
        for lead in self.lead_times:
            delay_seconds = (appointment_dt - lead - now).total_seconds()
            if delay_seconds <= 0:
                continue  # No duplicar recordatorios pasados
            message = (
                f"Hola {patient_name},\n\n"
                f"Falta {self._humanize_delta(lead)} para tu turno con {doctor_name} de {specialty} "
                f"el {date_str} a las {time_str}.\n"
                "Lo esperamos!\nConsultorio Médico Privado - Chacabuco 1244, Nueva Córdoba, Córdoba."
            )
            timer = threading.Timer(delay_seconds, subject.notify, args=(message,))
            timer.daemon = True
            timer.start()
            timers.append(timer)
        return timers

    @staticmethod
    def _humanize_delta(delta: timedelta) -> str:
        minutes = int(delta.total_seconds() // 60)
        if minutes % 1440 == 0:
            days = minutes // 1440
            return f"{days} día" + ("s" if days > 1 else "")
        if minutes % 60 == 0:
            hours = minutes // 60
            return f"{hours} hora" + ("s" if hours > 1 else "")
        return f"{minutes} minuto" + ("s" if minutes > 1 else "")
