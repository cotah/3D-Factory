"""Celery application for async AI jobs.

Phase 1 only configures the app and exposes a trivial ``ping`` task so the
worker can be started and verified. Real brief/image/3D tasks land in later
phases under ``app/tasks/``.
"""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "print3d",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_time_limit=settings.runpod_timeout_seconds + 60,
)


@celery_app.task(name="print3d.ping")
def ping() -> str:
    """Health task used to confirm the worker is alive."""
    return "pong"
