import asyncio
import smtplib
import socket
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

from src.config import settings

logger = structlog.get_logger()


async def send_email(to: str, subject: str, html_body: str) -> bool:
    if not to:
        logger.warning("email_no_recipient", subject=subject)
        return False

    if not settings.email_host:
        logger.warning("email_not_configured", to=to, subject=subject)
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = settings.email_from
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        def _send():
            with smtplib.SMTP(settings.email_host, settings.email_port) as server:
                if settings.email_use_tls:
                    server.starttls()
                if settings.email_user:
                    server.login(settings.email_user, settings.email_password)
                server.send_message(msg)

        await asyncio.to_thread(_send)
        logger.info("email_sent", to=to, subject=subject)
        return True
    except (smtplib.SMTPException, socket.gaierror, OSError) as e:
        logger.error("email_failed", to=to, subject=subject, error=str(e))
        return False
