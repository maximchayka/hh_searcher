import json

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import decrypt_token
from app.models.search_template import SearchTemplate
from app.models.user import User
from app.schemas.search_template import (
    SearchParams,
    SearchTemplateCreate,
    SearchTemplateRead,
    SearchTemplateUpdate,
)
from app.services.hh_client import HHClient

router = APIRouter(prefix="/search", tags=["search"])

_HH_HEADERS = {"User-Agent": "JobAutoApply/1.0 (contact@example.com)"}


def _build_hh_params(sp: SearchParams, page: int = 0) -> dict:
    params: dict = {"page": page, "per_page": min(sp.per_page, 100)}

    full_text = sp.text.strip()
    if sp.excluded_text.strip():
        suffix = f" NOT ({sp.excluded_text.strip()})"
        full_text = (full_text + suffix) if full_text else f"NOT ({sp.excluded_text.strip()})"
    if full_text:
        params["text"] = full_text

    if sp.search_field:
        params["search_field"] = sp.search_field
    if sp.area:
        params["area"] = sp.area
    if sp.experience:
        params["experience"] = sp.experience
    if sp.employment:
        params["employment"] = sp.employment
    if sp.schedule:
        params["schedule"] = sp.schedule
    if sp.salary and sp.salary > 0:
        params["salary"] = sp.salary
        params["currency_code"] = sp.currency_code
    if sp.only_with_salary:
        params["only_with_salary"] = "true"
    if sp.label:
        params["label"] = sp.label
    if sp.professional_role:
        params["professional_role"] = sp.professional_role
    if sp.industry:
        params["industry"] = sp.industry
    if sp.date_from:
        params["date_from"] = sp.date_from
    if sp.date_to:
        params["date_to"] = sp.date_to
    if sp.order_by:
        params["order_by"] = sp.order_by

    return params


@router.get("/vacancies")
async def search_vacancies(
    text: str = Query(""),
    search_field: list[str] = Query(default=[]),
    excluded_text: str = Query(""),
    area: list[str] = Query(default=[]),
    experience: str = Query(""),
    employment: list[str] = Query(default=[]),
    schedule: list[str] = Query(default=[]),
    salary: int | None = Query(None),
    currency_code: str = Query("RUR"),
    only_with_salary: bool = Query(False),
    label: list[str] = Query(default=[]),
    professional_role: list[str] = Query(default=[]),
    industry: list[str] = Query(default=[]),
    date_from: str = Query(""),
    date_to: str = Query(""),
    order_by: str = Query("publication_time"),
    per_page: int = Query(20),
    page: int = Query(0),
    template_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.hh_access_token:
        raise HTTPException(status_code=400, detail="hh.ru account not connected")

    if template_id:
        result = await db.execute(
            select(SearchTemplate).where(
                SearchTemplate.id == template_id,
                SearchTemplate.user_id == current_user.id,
            )
        )
        tmpl = result.scalar_one_or_none()
        if not tmpl:
            raise HTTPException(status_code=404, detail="Search template not found")
        try:
            sp = SearchParams(**json.loads(tmpl.params))
        except Exception:
            sp = SearchParams()
    else:
        sp = SearchParams(
            text=text,
            search_field=search_field,
            excluded_text=excluded_text,
            area=area,
            experience=experience,
            employment=employment,
            schedule=schedule,
            salary=salary,
            currency_code=currency_code,
            only_with_salary=only_with_salary,
            label=label,
            professional_role=professional_role,
            industry=industry,
            date_from=date_from,
            date_to=date_to,
            order_by=order_by,
            per_page=per_page,
        )

    hh_params = _build_hh_params(sp, page)
    hh = HHClient(decrypt_token(current_user.hh_access_token))
    return await hh.search_vacancies(hh_params)


@router.get("/dictionaries/areas")
async def get_areas(current_user: User = Depends(get_current_user)):
    """Returns a flat list of Russian regions from hh.ru."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://api.hh.ru/areas/113", headers=_HH_HEADERS)
            resp.raise_for_status()
            russia = resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to fetch areas from hh.ru")

    areas: list[dict] = []

    def _flatten(node: dict, depth: int) -> None:
        if 0 < depth <= 2:
            areas.append({"id": node["id"], "name": node["name"]})
        if depth < 2:
            for child in node.get("areas", []):
                _flatten(child, depth + 1)

    _flatten(russia, 0)
    return sorted(areas, key=lambda x: x["name"])


@router.get("/dictionaries/professional-roles")
async def get_professional_roles(current_user: User = Depends(get_current_user)):
    """Returns professional roles grouped by category from hh.ru."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.hh.ru/professional_roles", headers=_HH_HEADERS
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        raise HTTPException(
            status_code=502, detail="Failed to fetch professional roles from hh.ru"
        )

    roles: list[dict] = []
    for category in data.get("categories", []):
        for role in category.get("roles", []):
            roles.append(
                {"id": role["id"], "name": role["name"], "category": category["name"]}
            )
    return sorted(roles, key=lambda x: x["name"])


@router.post("/templates", response_model=SearchTemplateRead, status_code=201)
async def create_template(
    payload: SearchTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tmpl = SearchTemplate(
        user_id=current_user.id,
        name=payload.name,
        params=json.dumps(payload.params.model_dump(), ensure_ascii=False),
    )
    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.get("/templates", response_model=list[SearchTemplateRead])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SearchTemplate).where(SearchTemplate.user_id == current_user.id)
    )
    return result.scalars().all()


@router.put("/templates/{template_id}", response_model=SearchTemplateRead)
async def update_template(
    template_id: int,
    payload: SearchTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SearchTemplate).where(
            SearchTemplate.id == template_id,
            SearchTemplate.user_id == current_user.id,
        )
    )
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    if payload.name is not None:
        tmpl.name = payload.name
    if payload.params is not None:
        tmpl.params = json.dumps(payload.params.model_dump(), ensure_ascii=False)
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(SearchTemplate).where(
            SearchTemplate.id == template_id,
            SearchTemplate.user_id == current_user.id,
        )
    )
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.delete(tmpl)
    await db.commit()
