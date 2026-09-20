"""Profile database model — stores parsed resume data."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Profile(Base):
    """Stores the structured resume data extracted from a user's uploaded PDF."""

    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # ── Structured resume data (stored as JSONB for flexibility) ──────────
    personal_info: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # name, email, phone, location, linkedin_url, portfolio_url
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    work_experiences: Mapped[list | None] = mapped_column(
        JSONB, nullable=True
    )  # [{company, title, start_date, end_date, location, bullets: [...]}]
    education: Mapped[list | None] = mapped_column(
        JSONB, nullable=True
    )  # [{institution, degree, field, start_date, end_date, gpa}]
    skills: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # {technical: [...], soft: [...], languages: [...], tools: [...]}
    certifications: Mapped[list | None] = mapped_column(
        JSONB, nullable=True
    )  # [{name, issuer, date, credential_id}]
    projects: Mapped[list | None] = mapped_column(
        JSONB, nullable=True
    )  # [{name, description, technologies, url}]

    # ── Metadata ──────────────────────────────────────────────────────────
    raw_resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    parsed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="profile")  # type: ignore[name-defined]
    generated_cvs: Mapped[list["GeneratedCV"]] = relationship(  # type: ignore[name-defined]
        back_populates="profile", lazy="selectin"
    )
