import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ApplicationStatus(str, enum.Enum):
    SENT = "sent"
    VIEWED = "viewed"
    INVITATION = "invitation"
    REJECTION = "rejection"
    DISCARD = "discard"


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    vacancy_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    vacancy_title: Mapped[str] = mapped_column(String, nullable=False)
    company_name: Mapped[str] = mapped_column(String, nullable=False)
    salary_display: Mapped[str | None] = mapped_column(String, nullable=True)
    vacancy_url: Mapped[str] = mapped_column(String, nullable=False)

    resume_hh_id: Mapped[str] = mapped_column(String, nullable=False)
    cover_letter_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[ApplicationStatus] = mapped_column(Enum(ApplicationStatus), default=ApplicationStatus.SENT)
    hh_negotiation_id: Mapped[str | None] = mapped_column(String, nullable=True)

    job_task_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("job_tasks.id"), nullable=True)

    applied_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="applications")
