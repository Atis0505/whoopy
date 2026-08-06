"""Tranzakciós e-mail stub — SMTP ha van, különben log / fájl."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from pathlib import Path

from app.config import BASE_DIR, settings

logger = logging.getLogger(__name__)
OUTBOX = BASE_DIR / "data" / "email_outbox"


def send_mail(*, to: str, subject: str, body: str, html: str | None = None) -> bool:
    to = (to or "").strip()
    if not to:
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.admin_email
    msg["To"] = to
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")

    if settings.smtp_host and settings.smtp_user:
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
                if settings.smtp_use_tls:
                    smtp.starttls()
                if settings.smtp_password:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)
            logger.info("Email sent to %s: %s", to, subject)
            return True
        except Exception:
            logger.exception("SMTP send failed → falling back to outbox file")

    OUTBOX.mkdir(parents=True, exist_ok=True)
    safe = "".join(c if c.isalnum() or c in "-_@" else "_" for c in to)[:80]
    path = OUTBOX / f"{safe}_{abs(hash(subject + body)) % 10_000_000}.eml"
    path.write_bytes(msg.as_bytes())
    logger.info("Email written to outbox %s", path)
    return True


def order_confirmation_email(order) -> None:
    lines = "\n".join(
        f"- {ln.product_title} x{ln.quantity} = {ln.line_total:.0f} {order.currency}"
        for ln in (order.lines or [])
    )
    body = (
        f"Kedves {order.full_name}!\n\n"
        f"Rendelésed megérkezett: {order.order_number}\n"
        f"Összeg: {order.grand_total:.0f} {order.currency}\n"
        f"ÁFA ({order.tax_rate_percent}%): {getattr(order, 'tax_total', 0):.0f}\n\n"
        f"Tételek:\n{lines}\n\n"
        f"Köszönjük a vásárlást!\nWhoopy.hu\n"
    )
    send_mail(to=order.email, subject=f"Whoopy rendelés {order.order_number}", body=body)
