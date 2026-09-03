from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class Customer(Base):
    __tablename__ = "customers"

    # =========================================================
    # INTERNAL DATABASE ID
    # =========================================================

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # =========================================================
    # EXISTING EXTERNAL CUSTOMER ID
    # =========================================================

    external_customer_id: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    # =========================================================
    # CUSTOMER ACCESS ID
    # =========================================================
    #
    # This is the customer-facing secret/access identifier.
    #
    # Examples:
    #   CUST-7K4M2P
    #   CUST-X91Q8A
    #   CUST-4N6TZ9
    #
    # It is NOT the internal database primary key.
    # It will be generated separately for every customer.
    #
    # nullable=True for now because existing customers do not
    # have access IDs yet. After we generate IDs for all
    # customers, we will make this column NOT NULL through
    # a later migration.
    # =========================================================

    customer_access_id: Mapped[str | None] = mapped_column(
        String(50),
        unique=True,
        nullable=True,
        index=True,
    )

    # =========================================================
    # CUSTOMER INFORMATION
    # =========================================================

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )

    # =========================================================
    # CUSTOMER FINANCIAL METRICS
    # =========================================================

    lifetime_value: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=0,
    )

    successful_payments: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    failed_payments: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # =========================================================
    # CUSTOMER PREFERENCES
    # =========================================================

    opted_out: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    # =========================================================
    # TIMESTAMP
    # =========================================================

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    # =========================================================
    # RELATIONSHIPS
    # =========================================================

    transactions: Mapped[list["Transaction"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    recovery_cases: Mapped[list["RecoveryCase"]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )