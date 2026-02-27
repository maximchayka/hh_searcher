"""Celery tasks for periodic job monitoring and auto-apply."""
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

from celery import Task
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# Frequency → interval in seconds
FREQ_INTERVALS = {
    "15min": 15 * 60,
    "30min": 30 * 60,
    "1h":    60 * 60,
    "daily": 24 * 60 * 60,
}


def run_async(coro):
    """Run coroutine in a fresh event loop (Celery workers are synchronous)."""
    return asyncio.run(coro)


def _make_session():
    """Create a fresh DB session with NullPool — safe for Celery prefork workers."""
    from app.core.config import settings
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    return async_sessionmaker(engine, expire_on_commit=False)


def _is_due(task) -> bool:
    """Return True if the job task is due for execution."""
    now = datetime.now(timezone.utc)

    if task.frequency.value == "custom" and task.custom_cron:
        try:
            from croniter import croniter
            itr = croniter(task.custom_cron, task.last_run_at or task.created_at)
            next_run = itr.get_next(datetime)
            return now >= next_run
        except Exception:
            pass  # fall through to default

    interval = FREQ_INTERVALS.get(task.frequency.value, 3600)
    if task.last_run_at is None:
        return True
    return (now - task.last_run_at).total_seconds() >= interval


@celery_app.task
def check_due_tasks() -> dict:
    """
    Runs every 60 s via Celery Beat.
    Finds all ACTIVE job tasks that are due and dispatches run_job_task for each.
    """
    return run_async(_check_due_tasks_async())


async def _check_due_tasks_async() -> dict:
    from sqlalchemy import select
    from app.models.job_task import JobTask, TaskStatus

    dispatched = []
    async with _make_session()() as db:
        result = await db.execute(
            select(JobTask).where(JobTask.status == TaskStatus.ACTIVE)
        )
        tasks = result.scalars().all()

        for task in tasks:
            if _is_due(task):
                run_job_task.delay(task.id)
                task.last_run_at = datetime.now(timezone.utc)
                dispatched.append(task.id)

        if dispatched:
            await db.commit()

    return {"dispatched": dispatched}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_job_task(self: Task, job_task_id: int) -> dict:
    """Execute a single job task: search → filter → apply → log."""
    return run_async(_run_job_task_async(self, job_task_id))


async def _run_job_task_async(task: Task, job_task_id: int) -> dict:
    from sqlalchemy import select
    from app.core.security import decrypt_token
    from app.models.job_task import JobTask, JobTaskLog, TaskStatus
    from app.models.cover_letter import CoverLetterTemplate
    from app.services.hh_client import HHClient
    from app.services.apply import submit_applications

    async with _make_session()() as db:
        result = await db.execute(select(JobTask).where(JobTask.id == job_task_id))
        job_task = result.scalar_one_or_none()
        if not job_task or job_task.status != TaskStatus.ACTIVE:
            return {"skipped": True}

        log = JobTaskLog(job_task_id=job_task_id)
        db.add(log)
        await db.commit()
        await db.refresh(log)

        try:
            user = job_task.user
            if not user.hh_access_token:
                raise ValueError("User has no hh.ru token")

            hh = HHClient(decrypt_token(user.hh_access_token))

            search_params = json.loads(job_task.search_template.params)
            search_result = await hh.search_vacancies(search_params)
            items = search_result.get("items", [])
            vacancy_ids = [v["id"] for v in items][: job_task.per_run_limit]

            cover_letter_body = None
            if job_task.cover_letter_template_id:
                tmpl_res = await db.execute(
                    select(CoverLetterTemplate).where(
                        CoverLetterTemplate.id == job_task.cover_letter_template_id
                    )
                )
                tmpl = tmpl_res.scalar_one_or_none()
                if tmpl:
                    cover_letter_body = tmpl.body

            active_resume = next((r for r in user.resumes if r.is_active), None)
            if not active_resume:
                raise ValueError("No active resume found")

            result_data = await submit_applications(
                db=db,
                hh_client=hh,
                user_id=user.id,
                vacancy_ids=vacancy_ids,
                resume_hh_id=active_resume.hh_resume_id,
                cover_letter_template_body=cover_letter_body,
                daily_limit=job_task.daily_limit,
            )

            log.vacancies_found = len(items)
            log.applied_count = len(result_data["applied"])
            log.errors_count = len(result_data["errors"])
            log.finished_at = datetime.now(timezone.utc)
            log.status = "success"
            await db.commit()
            return result_data

        except Exception as exc:
            logger.exception("Job task %d failed", job_task_id)
            log.errors_detail = str(exc)
            log.finished_at = datetime.now(timezone.utc)
            log.status = "error"
            job_task.status = TaskStatus.ERROR
            await db.commit()
            raise
