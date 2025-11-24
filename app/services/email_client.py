import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional


class EmailClient:
    def __init__(
        self,
        smtp_server: str = None,
        smtp_port: int = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        sender: Optional[str] = None,
        dry_run: Optional[bool] = None,
        use_ssl: Optional[bool] = None,
    ) -> None:
        self.smtp_server = smtp_server or os.getenv("SMTP_SERVER", os.getenv("SMTP_HOST", "localhost"))
        self.smtp_port = smtp_port or int(os.getenv("SMTP_PORT", "25"))
        self.username = username or os.getenv("SMTP_USERNAME", os.getenv("SMTP_USER"))
        self.password = password or os.getenv("SMTP_PASSWORD", os.getenv("SMTP_PASS"))
        self.sender = sender or os.getenv("EMAIL_SENDER", self.username or "no-reply@mediflow.local")

        env_dry_run = os.getenv("SMTP_DRY_RUN")
        if dry_run is not None:
            self.dry_run = dry_run
        elif env_dry_run is not None:
            self.dry_run = env_dry_run.lower() == "true"
        else:
            self.dry_run = True

        # Usa SSL directo si se pide por env o si el puerto es el tipico 465.
        env_use_ssl = os.getenv("SMTP_USE_SSL")
        if env_use_ssl is not None:
            self.use_ssl = env_use_ssl.lower() == "true"
        elif use_ssl is not None:
            self.use_ssl = use_ssl
        else:
            self.use_ssl = self.smtp_port == 465

    def send_email(self, recipient: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.set_content(body)

        if self.dry_run:
            print(f"[DRY RUN EMAIL] To: {recipient} | Subject: {subject} | Body: {body}")
            return

        if self.use_ssl:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, context=context, timeout=10) as server:
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                if self.username and self.password:
                    server.starttls()
                    server.login(self.username, self.password)
                server.send_message(msg)
