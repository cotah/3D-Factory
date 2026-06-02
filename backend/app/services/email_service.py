"""Email notifications.

Falls back to logging when SMTP is not configured (so it never breaks the
request flow). Never logs credentials.
"""

from __future__ import annotations

from loguru import logger

from app.core.config import settings
from app.models.models import DesignerTask, Order, User


def _smtp_configured() -> bool:
    return bool(settings.smtp_host and settings.smtp_user)


def _deadline_text(task: DesignerTask) -> str:
    import json

    if task.notes:
        try:
            data = json.loads(task.notes)
            return str(data.get("deadline", "A definir"))[:10]
        except (json.JSONDecodeError, TypeError):
            pass
    return "A definir"


async def send_designer_notification(
    designer: User, order: Order, task: DesignerTask
) -> None:
    """Notify a designer about a new task. Logs instead if SMTP is off."""
    reference = f"ORD-{order.id:06d}"
    subject = f"Nova tarefa de design — {order.title}"
    body = (
        f"Olá {designer.full_name or designer.email},\n\n"
        "Você tem uma nova tarefa de design 3D.\n\n"
        f"Referência: {reference}\n"
        f"Categoria: {order.category or '-'}\n"
        f"Prazo: {_deadline_text(task)}\n\n"
        "Acesse o painel para ver o briefing completo e enviar o modelo.\n\n"
        "Print3D Platform"
    )

    if not _smtp_configured():
        logger.info("[EMAIL:MOCK] to={} subject={!r}", designer.email, subject)
        return

    try:
        import aiosmtplib
        from email.message import EmailMessage

        message = EmailMessage()
        message["From"] = settings.smtp_from_email
        message["To"] = designer.email
        message["Subject"] = subject
        message.set_content(body)

        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        logger.info("Designer notification sent to {}", designer.email)
    except Exception as exc:  # noqa: BLE001 - email must never break the flow
        logger.error("Failed to send designer email: {}", type(exc).__name__)
