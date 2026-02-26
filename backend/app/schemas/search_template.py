from datetime import datetime
from pydantic import BaseModel


class SearchParams(BaseModel):
    text: str = ""
    excluded_text: str = ""
    area: list[str] = []
    remote: bool = False
    salary_from: int | None = None
    salary_to: int | None = None
    experience: str = "noExperience"
    employment: list[str] = []
    schedule: list[str] = []
    employer_id: str | None = None
    date_from: str | None = None
    order_by: str = "publication_time"


class SearchTemplateCreate(BaseModel):
    name: str
    params: SearchParams


class SearchTemplateUpdate(BaseModel):
    name: str | None = None
    params: SearchParams | None = None


class SearchTemplateRead(BaseModel):
    id: int
    name: str
    params: str  # raw JSON
    created_at: datetime

    model_config = {"from_attributes": True}
