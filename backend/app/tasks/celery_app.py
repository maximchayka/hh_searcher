from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "jobautoapply",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.tasks.job_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Built-in file-based scheduler — no external dependencies
    beat_schedule={
        "check-due-job-tasks": {
            "task": "app.tasks.job_tasks.check_due_tasks",
            "schedule": 60.0,  # every 60 seconds
        },
    },
)
