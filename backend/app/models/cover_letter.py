"""GeneratedCoverLetter database model — stores AI-generated cover letters."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GeneratedCoverLetter(Base):
    """Stores a concise generated cover letter tied to a user, profile, and job description."""

    __tablename__ = "generated_cover_letters"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
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
    cover_letter_text: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="generated_cover_letters")  # type: ignore[name-defined]
    profile: Mapped["Profile | None"] = relationship(back_populates="generated_cover_letters")  # type: ignore[name-defined]

