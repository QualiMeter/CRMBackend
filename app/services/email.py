from __future__ import annotations
import asyncio, smtplib
from email.message import EmailMessage
from app.core.config import settings

async def send_email(to: str, subject: str, body: str) -> bool:
    if not settings.smtp_host or not settings.smtp_from:
        return False
    def _send():
        msg=EmailMessage(); msg["From"]=settings.smtp_from; msg["To"]=to; msg["Subject"]=subject; msg.set_content(body)
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            if settings.smtp_starttls: server.starttls()
            if settings.smtp_username: server.login(settings.smtp_username, settings.smtp_password or "")
            server.send_message(msg)
    await asyncio.to_thread(_send)
    return True
