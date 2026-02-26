from datetime import datetime
from pydantic import BaseModel


class CoverLetterTemplateCreate(BaseModel):
    name: str
    body: str


class CoverLetterTemplateUpdate(BaseModel):
    name: str | None = None
    body: str | None = None


class CoverLetterTemplateRead(BaseModel):
    id: int
    name: str
    body: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CoverLetterGenerate(BaseModel):
    vacancy_id: str
    tone: str = "formal"  # formal | informal
    length: str = "short"  # short | detailed
