import json
import random
import secrets
from datetime import datetime, timedelta, timezone

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import (
    create_access_token,
    decrypt_token,
    encrypt_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import HHAuthCallback, OTPVerify, Token, UserCreate, UserRead
from app.services.email_service import send_otp_email
from app.services.hh_client import HHClient

router = APIRouter(prefix="/auth", tags=["auth"])

ALLOWED_DOMAINS = {"infoteq.ru", "iq-cloud.ru"}
OTP_TTL = 900  # 15 minutes


def _redis() -> aioredis.Redis:
    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


@router.post("/register", status_code=status.HTTP_200_OK)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    domain = payload.email.split("@")[1].lower()
    if domain not in ALLOWED_DOMAINS:
        raise HTTPException(
            status_code=400,
            detail="Регистрация доступна только для @infoteq.ru и @iq-cloud.ru",
        )

    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

    otp = str(random.randint(100000, 999999))

    async with _redis() as r:
        await r.setex(
            f"otp:{payload.email}",
            OTP_TTL,
            json.dumps({"hashed_password": hash_password(payload.password), "otp": otp}),
        )

    try:
        await send_otp_email(payload.email, otp)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Не удалось отправить письмо: {exc}",
        )

    return {"message": "Код подтверждения отправлен на email"}


@router.post("/verify-otp", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def verify_otp(payload: OTPVerify, db: AsyncSession = Depends(get_db)):
    async with _redis() as r:
        stored_raw = await r.get(f"otp:{payload.email}")
        if not stored_raw:
            raise HTTPException(
                status_code=400,
                detail="Код истёк или не найден. Запросите новый.",
            )
        stored = json.loads(stored_raw)
        if not secrets.compare_digest(stored["otp"], payload.otp):
            raise HTTPException(status_code=400, detail="Неверный код подтверждения")
        await r.delete(f"otp:{payload.email}")

    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

    user = User(
        email=payload.email,
        hashed_password=stored["hashed_password"],
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password or ""):
        raise HTTPException(status_code=401, detail="Неверные данные")
    token = create_access_token(user.id)
    return Token(access_token=token)


@router.get("/hh/url")
async def hh_auth_url(current_user: User = Depends(get_current_user)):
    url = HHClient.get_auth_url(state=str(current_user.id))
    return {"url": url}


@router.post("/hh/callback")
async def hh_callback(
    payload: HHAuthCallback,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        token_data = await HHClient.exchange_code(payload.code)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"hh.ru token exchange failed: {exc}")

    expires_in = token_data.get("expires_in", 86400)
    current_user.hh_access_token = encrypt_token(token_data["access_token"])
    current_user.hh_refresh_token = encrypt_token(token_data["refresh_token"])
    current_user.hh_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    await db.commit()
    return {"status": "connected"}


@router.get("/me", response_model=UserRead)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
