import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import decrypt_token
from app.models.resume import Resume
from app.models.user import User
from app.schemas.resume import ResumeRead, ResumeSetActive
from app.services.hh_client import HHClient

router = APIRouter(prefix="/resumes", tags=["resumes"])


@router.post("/sync", response_model=list[ResumeRead])
async def sync_resumes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.hh_access_token:
        raise HTTPException(status_code=400, detail="hh.ru account not connected")

    hh = HHClient(decrypt_token(current_user.hh_access_token))
    hh_resumes = await hh.get_resumes()

    result = await db.execute(select(Resume).where(Resume.user_id == current_user.id))
    existing = {r.hh_resume_id: r for r in result.scalars().all()}

    synced = []
    for r in hh_resumes:
        resume = existing.get(r["id"])
        if not resume:
            resume = Resume(user_id=current_user.id, hh_resume_id=r["id"])
            db.add(resume)

        resume.title = r.get("title", "")
        resume.first_name = r.get("first_name")
        resume.last_name = r.get("last_name")
        resume.raw_data = json.dumps(r, ensure_ascii=False)
        synced.append(resume)

    await db.commit()
    for s in synced:
        await db.refresh(s)
    return synced


@router.get("/", response_model=list[ResumeRead])
async def list_resumes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Resume).where(Resume.user_id == current_user.id))
    return result.scalars().all()


@router.post("/set-active")
async def set_active_resume(
    payload: ResumeSetActive,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Resume).where(Resume.user_id == current_user.id))
    resumes = result.scalars().all()
    found = False
    for r in resumes:
        r.is_active = r.id == payload.resume_id
        if r.is_active:
            found = True
    if not found:
        raise HTTPException(status_code=404, detail="Resume not found")
    await db.commit()
    return {"status": "ok"}
