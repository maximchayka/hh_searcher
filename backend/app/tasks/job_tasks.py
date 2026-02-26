"""Celery tasks for periodic job monitoring and auto-apply."""
import asyncio
import json
import logging
from datetime import datetime, timezone

from celery import Task

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run coroutine in new event loop (Celery workers are sync)."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_job_task(self: Task, job_task_id: int) -> dict:
    """Main periodic task: search, filter, apply."""
    return run_async(_run_job_task_async(self, job_task_id))


async def _run_job_task_async(task: Task, job_task_id: int) -> dict:
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.core.security import decrypt_token
    from app.models.job_task import JobTask, JobTaskLog, TaskStatus
    from app.models.search_template import SearchTemplate
    from app.models.cover_letter import CoverLetterTemplate
    from app.services.hh_client import HHClient
    from app.services.apply import submit_applications

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(JobTask).where(JobTask.id == job_task_id))
        job_task = result.scalar_one_or_none()
        if not job_task or job_task.status not in (TaskStatus.ACTIVE,):
            return {"skipped": True}

        log = JobTaskLog(job_task_id=job_task_id)
        db.add(log)
        await db.commit()
        await db.refresh(log)

        try:
            user = job_task.user
            if not user.hh_access_token:
                raise ValueError("User has no hh.ru token")

            access_token = decrypt_token(user.hh_access_token)
            hh = HHClient(access_token)

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

            active_resume = None
            for resume in user.resumes:
                if resume.is_active:
                    active_resume = resume
                    break

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
