from datetime import datetime
from pydantic import BaseModel

from app.models.application import ApplicationStatus


class ApplyRequest(BaseModel):
    vacancy_ids: list[str]
    resume_hh_id: str
    cover_letter_template_id: int | None = None
    ai_cover_letter: bool = False


class ApplicationRead(BaseModel):
    id: int
    vacancy_id: str
    vacancy_title: str
    company_name: str
    salary_display: str | None
    vacancy_url: str
    resume_hh_id: str
    cover_letter_text: str | None
    status: ApplicationStatus
    applied_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApplicationStats(BaseModel):
    total: int
    sent: int
    viewed: int
    invitation: int
    rejection: int
