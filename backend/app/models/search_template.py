from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SearchTemplate(Base):
    """
    Stores saved job search parameters as JSON in `params` field.
    Params schema: {
        "text": str,
        "excluded_text": str,
        "area": list[str],          # region IDs
        "remote": bool,
        "salary_from": int | null,
        "salary_to": int | null,
        "experience": str,          # hh.ru experience values
        "employment": list[str],
        "schedule": list[str],
        "employer_id": str | null,
        "date_from": str | null,    # ISO date
        "order_by": str,
    }
    """

    __tablename__ = "search_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    name: Mapped[str] = mapped_column(String, nullable=False)
    params: Mapped[str] = mapped_column(Text, nullable=False)  # JSON

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="search_templates")
    job_tasks: Mapped[list["JobTask"]] = relationship("JobTask", back_populates="search_template")
