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
        subject = "Recordatorio de turno"
        body = f"Hola {self.name},\n\n{data}\n\nConsultorio Médico."
        self.email_client.send_email(self.email, subject, body)


class ReminderSubject(Subject):
    """Sujeto que notifica a los observadores (pacientes) mensajes de recordatorio."""

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
        self, appointment_dt: datetime, patient_name: str, patient_email: str
    ) -> List[threading.Timer]:
        """Programa timers en memoria; suficiente para la demo y tests."""
        subject = ReminderSubject()
        subject.attach(PatientObserver(patient_name, patient_email, self.email_client))
        timers: List[threading.Timer] = []
        now = datetime.now()
        for lead in self.lead_times:
            delay_seconds = (appointment_dt - lead - now).total_seconds()
            if delay_seconds <= 0:
                # Si ya pasó la ventana, notifica de inmediato.
                subject.notify(f"Tienes un turno el {appointment_dt.isoformat(sep=' ', timespec='minutes')}.")
                continue
            message = f"Falta {self._humanize_delta(lead)} para tu turno el {appointment_dt.isoformat(sep=' ', timespec='minutes')}."
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
