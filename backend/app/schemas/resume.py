from datetime import datetime
from pydantic import BaseModel


class ResumeRead(BaseModel):
    id: int
    hh_resume_id: str
    title: str
    first_name: str | None
    last_name: str | None
    skills: str | None
    is_active: bool
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeSetActive(BaseModel):
    resume_id: int
