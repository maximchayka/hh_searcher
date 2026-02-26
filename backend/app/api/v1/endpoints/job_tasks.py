from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.job_task import JobTask, JobTaskLog, TaskStatus
from app.models.user import User
from app.schemas.job_task import JobTaskCreate, JobTaskLogRead, JobTaskRead, JobTaskUpdate
from app.tasks.job_tasks import run_job_task

router = APIRouter(prefix="/job-tasks", tags=["job-tasks"])


@router.post("/", response_model=JobTaskRead, status_code=201)
async def create_task(
    payload: JobTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = JobTask(user_id=current_user.id, **payload.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    _schedule_task(task)
    return task


@router.get("/", response_model=list[JobTaskRead])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(JobTask).where(JobTask.user_id == current_user.id))
    return result.scalars().all()


@router.get("/{task_id}", response_model=JobTaskRead)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(JobTask).where(JobTask.id == task_id, JobTask.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=JobTaskRead)
async def update_task(
    task_id: int,
    payload: JobTaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(JobTask).where(JobTask.id == task_id, JobTask.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(task, field, value)
    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(JobTask).where(JobTask.id == task_id, JobTask.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.commit()


@router.post("/{task_id}/run")
async def run_task_now(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(JobTask).where(JobTask.id == task_id, JobTask.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    celery_task = run_job_task.delay(task_id)
    return {"celery_task_id": celery_task.id}


@router.get("/{task_id}/logs", response_model=list[JobTaskLogRead])
async def get_task_logs(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(JobTask).where(JobTask.id == task_id, JobTask.user_id == current_user.id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    logs_result = await db.execute(
        select(JobTaskLog)
        .where(JobTaskLog.job_task_id == task_id)
        .order_by(JobTaskLog.started_at.desc())
        .limit(50)
    )
    return logs_result.scalars().all()


def _schedule_task(task: JobTask):
    """Register task with Celery Beat via RedBeat."""
    from redbeat import RedBeatSchedulerEntry
    from celery.schedules import crontab, schedule as celery_schedule
    from datetime import timedelta
    from app.tasks.celery_app import celery_app

    freq_map = {
        "15min": celery_schedule(timedelta(minutes=15)),
        "30min": celery_schedule(timedelta(minutes=30)),
        "1h": celery_schedule(timedelta(hours=1)),
        "daily": celery_schedule(timedelta(days=1)),
    }

    if task.frequency.value == "custom" and task.custom_cron:
        parts = task.custom_cron.split()
        if len(parts) == 5:
            sched = crontab(
                minute=parts[0], hour=parts[1],
                day_of_month=parts[2], month_of_year=parts[3], day_of_week=parts[4]
            )
        else:
            sched = freq_map["1h"]
    else:
        sched = freq_map.get(task.frequency.value, freq_map["1h"])

    entry = RedBeatSchedulerEntry(
        name=f"job_task_{task.id}",
        task="app.tasks.job_tasks.run_job_task",
        schedule=sched,
        args=[task.id],
        app=celery_app,
    )
    entry.save()
