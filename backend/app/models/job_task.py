import enum
from datetime import datetime
from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Integer, String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TaskFrequency(str, enum.Enum):
    MINUTES_15 = "15min"
    MINUTES_30 = "30min"
    HOURLY = "1h"
    DAILY = "daily"
    CUSTOM = "custom"


class TaskAction(str, enum.Enum):
    AUTO_APPLY = "auto_apply"
    MANUAL_REVIEW = "manual_review"
    NOTIFY_ONLY = "notify_only"


class TaskStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"
    COMPLETED = "completed"
    LIMIT_REACHED = "limit_reached"


class JobTask(Base):
    __tablename__ = "job_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    search_template_id: Mapped[int] = mapped_column(Integer, ForeignKey("search_templates.id"), nullable=False)
    cover_letter_template_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("cover_letter_templates.id"), nullable=True
    )

    name: Mapped[str] = mapped_column(String, nullable=False)
    frequency: Mapped[TaskFrequency] = mapped_column(Enum(TaskFrequency), nullable=False)
    custom_cron: Mapped[str | None] = mapped_column(String, nullable=True)

    action: Mapped[TaskAction] = mapped_column(Enum(TaskAction), default=TaskAction.AUTO_APPLY)
    status: Mapped[TaskStatus] = mapped_column(Enum(TaskStatus), default=TaskStatus.ACTIVE)

    only_new: Mapped[bool] = mapped_column(Boolean, default=True)
    skip_applied: Mapped[bool] = mapped_column(Boolean, default=True)
    min_ai_match: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 0-100

    daily_limit: Mapped[int] = mapped_column(Integer, default=50)
    per_run_limit: Mapped[int] = mapped_column(Integer, default=20)
    per_company_limit: Mapped[int] = mapped_column(Integer, default=3)

    # Celery Beat task ID for dynamic scheduling
    celery_task_id: Mapped[str | None] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="job_tasks")
    search_template: Mapped["SearchTemplate"] = relationship("SearchTemplate", back_populates="job_tasks")
    logs: Mapped[list["JobTaskLog"]] = relationship("JobTaskLog", back_populates="job_task", cascade="all, delete-orphan")


class JobTaskLog(Base):
    __tablename__ = "job_task_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_task_id: Mapped[int] = mapped_column(Integer, ForeignKey("job_tasks.id"), nullable=False)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    vacancies_found: Mapped[int] = mapped_column(Integer, default=0)
    applied_count: Mapped[int] = mapped_column(Integer, default=0)
    errors_count: Mapped[int] = mapped_column(Integer, default=0)
    errors_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String, default="running")

    job_task: Mapped["JobTask"] = relationship("JobTask", back_populates="logs")
