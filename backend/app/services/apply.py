"""Application submission logic with anti-spam controls."""
import asyncio
import json
import random
from datetime import datetime, date, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationStatus
from app.models.resume import Resume
from app.services.cover_letter import generate_ai_cover_letter, render_template
from app.services.hh_client import HHClient


async def count_today_applications(db: AsyncSession, user_id: int) -> int:
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)
    result = await db.execute(
        select(func.count(Application.id)).where(
            Application.user_id == user_id,
            Application.applied_at >= today_start,
        )
    )
    return result.scalar_one()


async def has_applied(db: AsyncSession, user_id: int, vacancy_id: str) -> bool:
    result = await db.execute(
        select(Application.id).where(
            Application.user_id == user_id,
            Application.vacancy_id == vacancy_id,
        )
    )
    return result.scalar_one_or_none() is not None


async def submit_applications(
    db: AsyncSession,
    hh_client: HHClient,
    user_id: int,
    vacancy_ids: list[str],
    resume_hh_id: str,
    cover_letter_template_body: str | None = None,
    ai_cover_letter: bool = False,
    daily_limit: int = 50,
    delay_range: tuple[float, float] = (3.0, 8.0),
) -> dict:
    applied = []
    skipped = []
    errors = []

    today_count = await count_today_applications(db, user_id)

    for vacancy_id in vacancy_ids:
        if today_count >= daily_limit:
            skipped.append({"vacancy_id": vacancy_id, "reason": "daily_limit_reached"})
            continue

        if await has_applied(db, user_id, vacancy_id):
            skipped.append({"vacancy_id": vacancy_id, "reason": "already_applied"})
            continue

        try:
            vacancy = await hh_client.get_vacancy(vacancy_id)

            cover_letter = ""
            if ai_cover_letter:
                cover_letter = await generate_ai_cover_letter(vacancy, "")
            elif cover_letter_template_body:
                context = {
                    "company_name": vacancy.get("employer", {}).get("name", ""),
                    "vacancy_title": vacancy.get("name", ""),
                    "salary": _format_salary(vacancy.get("salary")),
                    "skills": "",
                    "hr_name": "",
                }
                cover_letter = render_template(cover_letter_template_body, context)

            await hh_client.apply_to_vacancy(vacancy_id, resume_hh_id, cover_letter)

            application = Application(
                user_id=user_id,
                vacancy_id=vacancy_id,
                vacancy_title=vacancy.get("name", ""),
                company_name=vacancy.get("employer", {}).get("name", ""),
                salary_display=_format_salary(vacancy.get("salary")),
                vacancy_url=vacancy.get("alternate_url", ""),
                resume_hh_id=resume_hh_id,
                cover_letter_text=cover_letter or None,
                status=ApplicationStatus.SENT,
            )
            db.add(application)
            await db.commit()

            applied.append(vacancy_id)
            today_count += 1

            delay = random.uniform(*delay_range)
            await asyncio.sleep(delay)

        except Exception as exc:
            await db.rollback()
            errors.append({"vacancy_id": vacancy_id, "error": str(exc)})

    return {"applied": applied, "skipped": skipped, "errors": errors}


def _format_salary(salary: dict | None) -> str | None:
    if not salary:
        return None
    parts = []
    if salary.get("from"):
        parts.append(f"от {salary['from']}")
    if salary.get("to"):
        parts.append(f"до {salary['to']}")
    currency = salary.get("currency", "")
    return " ".join(parts) + f" {currency}" if parts else None
