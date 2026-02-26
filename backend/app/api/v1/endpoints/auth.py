from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
from app.schemas.user import HHAuthCallback, Token, UserCreate, UserRead
from app.services.hh_client import HHClient

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=Token)
async def login(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password or ""):
        raise HTTPException(status_code=401, detail="Invalid credentials")
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
