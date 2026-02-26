from datetime import datetime
from pydantic import BaseModel

from app.models.job_task import TaskAction, TaskFrequency, TaskStatus


class JobTaskCreate(BaseModel):
    name: str
    search_template_id: int
    cover_letter_template_id: int | None = None
    frequency: TaskFrequency
    custom_cron: str | None = None
    action: TaskAction = TaskAction.AUTO_APPLY
    only_new: bool = True
    skip_applied: bool = True
    min_ai_match: int | None = None
    daily_limit: int = 50
    per_run_limit: int = 20
    per_company_limit: int = 3


class JobTaskUpdate(BaseModel):
    name: str | None = None
    cover_letter_template_id: int | None = None
    frequency: TaskFrequency | None = None
    custom_cron: str | None = None
    action: TaskAction | None = None
    status: TaskStatus | None = None
    only_new: bool | None = None
    skip_applied: bool | None = None
    min_ai_match: int | None = None
    daily_limit: int | None = None
    per_run_limit: int | None = None
    per_company_limit: int | None = None


class JobTaskRead(BaseModel):
    id: int
    name: str
    search_template_id: int
    cover_letter_template_id: int | None
    frequency: TaskFrequency
    custom_cron: str | None
    action: TaskAction
    status: TaskStatus
    only_new: bool
    skip_applied: bool
    min_ai_match: int | None
    daily_limit: int
    per_run_limit: int
    per_company_limit: int
    created_at: datetime

    model_config = {"from_attributes": True}


class JobTaskLogRead(BaseModel):
    id: int
    job_task_id: int
    started_at: datetime
    finished_at: datetime | None
    vacancies_found: int
    applied_count: int
    errors_count: int
    status: str

    model_config = {"from_attributes": True}
