from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import settings


async def send_otp_email(to_email: str, otp: str) -> None:
    message = MIMEMultipart("alternative")
    message["Subject"] = "Код подтверждения — JobAutoApply"
    message["From"] = settings.SMTP_FROM
    message["To"] = to_email

    text = (
        f"Ваш код подтверждения для регистрации в JobAutoApply: {otp}\n"
        "Код действителен 15 минут."
    )
    html = f"""<html><body>
<p>Ваш код подтверждения для регистрации в <strong>JobAutoApply</strong>:</p>
<h2 style="letter-spacing:4px">{otp}</h2>
<p style="color:#888">Код действителен 15 минут.</p>
</body></html>"""

    message.attach(MIMEText(text, "plain", "utf-8"))
    message.attach(MIMEText(html, "html", "utf-8"))

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        username=settings.SMTP_USER,
        password=settings.SMTP_PASSWORD,
        start_tls=settings.SMTP_TLS,
    )
