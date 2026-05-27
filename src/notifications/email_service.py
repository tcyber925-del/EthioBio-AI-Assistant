import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

logger = structlog.get_logger()


def get_email_config():
    return {
        "host": os.getenv("EMAIL_HOST", ""),
        "port": int(os.getenv("EMAIL_PORT", "587")),
        "user": os.getenv("EMAIL_USER", ""),
        "password": os.getenv("EMAIL_PASS", ""),
        "from": os.getenv("EMAIL_FROM", "noreply@ethiobio.com"),
        "use_tls": os.getenv("EMAIL_USE_TLS", "true").lower() == "true",
    }


def send_email(to: str, subject: str, html_body: str) -> bool:
    config = get_email_config()
    if not config["host"]:
        logger.warning("email_not_configured", to=to, subject=subject)
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = config["from"]
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(config["host"], config["port"]) as server:
            if config["use_tls"]:
                server.starttls()
            if config["user"]:
                server.login(config["user"], config["password"])
            server.send_message(msg)

        logger.info("email_sent", to=to, subject=subject)
        return True
    except Exception as e:
        logger.error("email_failed", to=to, subject=subject, error=str(e))
        return False
