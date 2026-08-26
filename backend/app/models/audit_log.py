from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    recovery_case_id: Mapped[int | None] = mapped_column(
        ForeignKey("recovery_cases.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    actor_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    actor_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    message: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    event_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )

    recovery_case: Mapped["RecoveryCase | None"] = relationship(
        back_populates="audit_logs",
    )