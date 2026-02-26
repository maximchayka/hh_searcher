import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import decrypt_token
from app.models.search_template import SearchTemplate
from app.models.user import User
from app.schemas.search_template import (
    SearchTemplateCreate,
    SearchTemplateRead,
    SearchTemplateUpdate,
)
from app.services.hh_client import HHClient

router = APIRouter(prefix="/search", tags=["search"])


@router.get("/vacancies")
async def search_vacancies(
    template_id: int | None = Query(None),
    text: str = Query(""),
    area: str = Query(""),
    remote: bool = Query(False),
    salary_from: int | None = Query(None),
    salary_to: int | None = Query(None),
    experience: str = Query(""),
    page: int = Query(0),
    per_page: int = Query(20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.hh_access_token:
        raise HTTPException(status_code=400, detail="hh.ru account not connected")

    params: dict = {"page": page, "per_page": per_page}

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
        params.update(json.loads(tmpl.params))
    else:
        if text:
            params["text"] = text
        if area:
            params["area"] = area
        if remote:
            params["schedule"] = "remote"
        if salary_from:
            params["salary"] = salary_from
        if experience:
            params["experience"] = experience

    hh = HHClient(decrypt_token(current_user.hh_access_token))
    data = await hh.search_vacancies(params)
    return data


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
