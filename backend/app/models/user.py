from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # hh.ru OAuth tokens (encrypted)
    hh_access_token: Mapped[str | None] = mapped_column(String, nullable=True)
    hh_refresh_token: Mapped[str | None] = mapped_column(String, nullable=True)
    hh_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    resumes: Mapped[list["Resume"]] = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    cover_letter_templates: Mapped[list["CoverLetterTemplate"]] = relationship(
        "CoverLetterTemplate", back_populates="user", cascade="all, delete-orphan"
    )
    search_templates: Mapped[list["SearchTemplate"]] = relationship(
        "SearchTemplate", back_populates="user", cascade="all, delete-orphan"
    )
    job_tasks: Mapped[list["JobTask"]] = relationship(
        "JobTask", back_populates="user", cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="user", cascade="all, delete-orphan"
    )
