"""GeneratedCV database model — stores AI-generated tailored CVs."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GeneratedCV(Base):
    """Stores a generated ATS-optimized CV tied to a user, profile, and job description."""

    __tablename__ = "generated_cvs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Job context ───────────────────────────────────────────────────────
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_description: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Generated content ─────────────────────────────────────────────────
    tailored_content: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True
    )  # Full structured CV data optimized for the job
    pdf_file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    ats_score: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # Estimated ATS keyword match percentage

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="generated_cvs")  # type: ignore[name-defined]
    profile: Mapped["Profile | None"] = relationship(back_populates="generated_cvs")  # type: ignore[name-defined]
