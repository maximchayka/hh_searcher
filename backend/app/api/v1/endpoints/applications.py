from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import decrypt_token
from app.models.application import Application, ApplicationStatus
from app.models.cover_letter import CoverLetterTemplate
from app.models.user import User
from app.schemas.application import ApplyRequest, ApplicationRead, ApplicationStats
from app.services.apply import submit_applications
from app.services.hh_client import HHClient

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("/apply")
async def apply(
    payload: ApplyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hh = HHClient(decrypt_token(current_user.hh_access_token))

    cover_letter_body = None
    if payload.cover_letter_template_id:
        result = await db.execute(
            select(CoverLetterTemplate).where(
                CoverLetterTemplate.id == payload.cover_letter_template_id,
                CoverLetterTemplate.user_id == current_user.id,
            )
        )
        tmpl = result.scalar_one_or_none()
        if tmpl:
            cover_letter_body = tmpl.body

    result = await submit_applications(
        db=db,
        hh_client=hh,
        user_id=current_user.id,
        vacancy_ids=payload.vacancy_ids,
        resume_hh_id=payload.resume_hh_id,
        cover_letter_template_body=cover_letter_body,
        ai_cover_letter=payload.ai_cover_letter,
    )
    return result


@router.get("/", response_model=list[ApplicationRead])
async def list_applications(
    status: ApplicationStatus | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = select(Application).where(Application.user_id == current_user.id)
    if status:
        query = query.where(Application.status == status)
    query = query.order_by(Application.applied_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/stats", response_model=ApplicationStats)
async def stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base = select(func.count(Application.id)).where(Application.user_id == current_user.id)

    async def count(status=None):
        q = base
        if status:
            q = q.where(Application.status == status)
        r = await db.execute(q)
        return r.scalar_one()

    total = await count()
    sent = await count(ApplicationStatus.SENT)
    viewed = await count(ApplicationStatus.VIEWED)
    invitation = await count(ApplicationStatus.INVITATION)
    rejection = await count(ApplicationStatus.REJECTION)

    return ApplicationStats(
        total=total, sent=sent, viewed=viewed, invitation=invitation, rejection=rejection
    )
