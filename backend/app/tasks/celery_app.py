"""Celery application configuration for async task processing."""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "zavis_linkedin",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Beat schedule for periodic tasks
    beat_schedule={
        "check-scheduled-jobs": {
            "task": "app.tasks.scraper_tasks.check_scheduled_jobs",
            "schedule": 60.0,  # check every 60 seconds
        },
    },
)

celery_app.autodiscover_tasks(["app.tasks"])
