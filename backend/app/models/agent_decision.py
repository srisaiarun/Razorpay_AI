from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class AgentDecision(Base):
    __tablename__ = "agent_decisions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    recovery_case_id: Mapped[int] = mapped_column(
        ForeignKey("recovery_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    decision: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    reasoning_summary: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    confidence: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )

    expected_recovery_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    policy_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        index=True,
    )

    requires_human_approval: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    recovery_case: Mapped["RecoveryCase"] = relationship(
        back_populates="agent_decisions",
    )
    recovery_actions: Mapped[list["RecoveryAction"]] = relationship(
        back_populates="agent_decision",
        cascade="all, delete-orphan",
    )