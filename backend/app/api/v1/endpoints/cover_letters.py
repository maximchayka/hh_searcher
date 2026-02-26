from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import decrypt_token
from app.models.cover_letter import CoverLetterTemplate
from app.models.user import User
from app.schemas.cover_letter import (
    CoverLetterGenerate,
    CoverLetterTemplateCreate,
    CoverLetterTemplateRead,
    CoverLetterTemplateUpdate,
)
from app.services.cover_letter import generate_ai_cover_letter
from app.services.hh_client import HHClient

router = APIRouter(prefix="/cover-letters", tags=["cover-letters"])


@router.post("/", response_model=CoverLetterTemplateRead, status_code=201)
async def create_template(
    payload: CoverLetterTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tmpl = CoverLetterTemplate(user_id=current_user.id, name=payload.name, body=payload.body)
    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.get("/", response_model=list[CoverLetterTemplateRead])
async def list_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CoverLetterTemplate).where(CoverLetterTemplate.user_id == current_user.id)
    )
    return result.scalars().all()


@router.put("/{template_id}", response_model=CoverLetterTemplateRead)
async def update_template(
    template_id: int,
    payload: CoverLetterTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CoverLetterTemplate).where(
            CoverLetterTemplate.id == template_id,
            CoverLetterTemplate.user_id == current_user.id,
        )
    )
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    if payload.name is not None:
        tmpl.name = payload.name
    if payload.body is not None:
        tmpl.body = payload.body
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CoverLetterTemplate).where(
            CoverLetterTemplate.id == template_id,
            CoverLetterTemplate.user_id == current_user.id,
        )
    )
    tmpl = result.scalar_one_or_none()
    if not tmpl:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.delete(tmpl)
    await db.commit()


@router.post("/generate")
async def generate_cover_letter(
    payload: CoverLetterGenerate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.hh_access_token:
        raise HTTPException(status_code=400, detail="hh.ru account not connected")

    hh = HHClient(decrypt_token(current_user.hh_access_token))
    vacancy = await hh.get_vacancy(payload.vacancy_id)

    active_resume = next((r for r in current_user.resumes if r.is_active), None)
    skills = active_resume.skills or "" if active_resume else ""

    text = await generate_ai_cover_letter(
        vacancy=vacancy,
        resume_skills=skills,
        tone=payload.tone,
        length=payload.length,
    )
    return {"text": text}
