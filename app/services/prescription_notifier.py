from datetime import datetime

from app.observers.base import Observer, Subject
from app.services.email_client import EmailClient


class PrescriptionObserver(Observer):
    def __init__(self, patient_name: str, patient_email: str, email_client: EmailClient) -> None:
        self.patient_name = patient_name
        self.patient_email = patient_email
        self.email_client = email_client

    def update(self, data: str) -> None:
        subject = "Nueva receta medica"
        self.email_client.send_email(self.patient_email, subject, data)


class PrescriptionSubject(Subject):
    def __init__(self) -> None:
        super().__init__()


class PrescriptionNotifier:
    def __init__(self, email_client: EmailClient) -> None:
        self.email_client = email_client

    def notify_prescription(
        self,
        patient_name: str,
        patient_email: str,
        doctor_name: str,
        description: str,
    ) -> None:
        subject = PrescriptionSubject()
        subject.attach(PrescriptionObserver(patient_name, patient_email, self.email_client))

        issued_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        message = (
            f"Hola {patient_name},\n\n"
            f"Tu medico {doctor_name} genero una nueva receta el {issued_at}.\n\n"
            "Detalle de la receta:\n"
            f"{description}\n\n"
            "Ante cualquier duda responde este correo o comunicate con tu medico.\n"
            "MediFlow"
        )
        subject.notify(message)
