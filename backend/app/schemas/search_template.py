from datetime import datetime

from pydantic import BaseModel


class SearchParams(BaseModel):
    text: str = ""
    search_field: list[str] = []  # name, company_name, description
    excluded_text: str = ""
    area: list[str] = []
    experience: str = ""  # noExperience, between1And3, between3And6, moreThan6
    employment: list[str] = []  # full, part, project, volunteer, probation
    schedule: list[str] = []  # fullDay, shift, flexible, remote, flyInFlyOut
    salary: int | None = None
    currency_code: str = "RUR"
    only_with_salary: bool = False
    label: list[str] = []  # not_from_agency, accredited_it, with_address, accept_handicapped, internship
    professional_role: list[str] = []
    industry: list[str] = []
    date_from: str = ""
    date_to: str = ""
    order_by: str = "publication_time"
    per_page: int = 20


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
