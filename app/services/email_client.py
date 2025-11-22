import os
import smtplib
from email.message import EmailMessage
from typing import Optional


class EmailClient:
    """Cliente simple sobre smtplib. Por defecto funciona en modo dry-run."""

    def __init__(
        self,
        smtp_server: str = None,
        smtp_port: int = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        sender: Optional[str] = None,
        dry_run: bool = True,
    ) -> None:
        self.smtp_server = smtp_server or os.getenv("SMTP_SERVER", "localhost")
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "25"))
        self.username = username or os.getenv("SMTP_USERNAME")
        self.password = password or os.getenv("SMTP_PASSWORD")
        self.sender = sender or os.getenv("EMAIL_SENDER", "no-reply@clinic.local")
        self.dry_run = dry_run or os.getenv("SMTP_DRY_RUN", "true").lower() == "true"

    def send_email(self, recipient: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.set_content(body)

        if self.dry_run:
            # En modo dry-run solo se deja traza en consola.
            print(f"[DRY RUN EMAIL] To: {recipient} | Subject: {subject} | Body: {body}")
            return

        with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
            if self.username and self.password:
                server.starttls()
                server.login(self.username, self.password)
            server.send_message(msg)
