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
