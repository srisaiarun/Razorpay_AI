from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.models.customer import Customer
from backend.app.models.recovery_case import RecoveryCase
from backend.app.models.transaction import Transaction


PROJECT_ROOT = Path(__file__).resolve().parents[4]

QUEUE_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "customer_recovery_queue.parquet"
)

MAX_CASES = 500


def get_or_create_customer(
    db: Session,
    customer_external_id: str,
    lifetime_value: Decimal,
    successful_payments: int,
) -> Customer:
    customer = (
        db.query(Customer)
        .filter(
            Customer.external_customer_id
            == customer_external_id
        )
        .first()
    )

    if customer is not None:
        return customer

    customer = Customer(
        external_customer_id=customer_external_id,
        name=f"Customer {customer_external_id}",
        email=(
            f"customer.{customer_external_id}"
            "@example.com"
        ),
        lifetime_value=lifetime_value,
        successful_payments=successful_payments,
        failed_payments=1,
        opted_out=False,
    )

    db.add(customer)
    db.flush()

    return customer


def create_transaction(
    db: Session,
    customer: Customer,
    customer_external_id: str,
    snapshot_date: datetime,
    amount: Decimal,
) -> Transaction:
    external_transaction_id = (
        f"recovery-seed-{customer_external_id}-"
        f"{snapshot_date.strftime('%Y%m%d%H%M%S')}"
    )

    existing = (
        db.query(Transaction)
        .filter(
            Transaction.external_transaction_id
            == external_transaction_id
        )
        .first()
    )

    if existing is not None:
        return existing

    transaction = Transaction(
        external_transaction_id=external_transaction_id,
        customer_id=customer.id,
        amount=amount,
        currency="GBP",
        status="FAILED",
        failure_reason="PAYMENT_FAILURE",
        payment_method="card",
        razorpay_payment_id=None,
        razorpay_order_id=None,
        created_at=snapshot_date,
        updated_at=snapshot_date,
    )

    db.add(transaction)
    db.flush()

    return transaction


def create_recovery_case(
    db: Session,
    transaction: Transaction,
    customer: Customer,
    amount_at_risk: Decimal,
    recovery_probability: Decimal,
) -> RecoveryCase | None:
    existing = (
        db.query(RecoveryCase)
        .filter(
            RecoveryCase.transaction_id
            == transaction.id
        )
        .first()
    )

    if existing is not None:
        return existing

    risk_score = (
        Decimal("1.0000")
        - recovery_probability
    )

    recovery_case = RecoveryCase(
        transaction_id=transaction.id,
        customer_id=customer.id,
        amount_at_risk=amount_at_risk,
        failure_class="PAYMENT_FAILURE",
        risk_score=risk_score,
        recovery_probability=recovery_probability,
        status="OPEN",
        attempt_count=0,
        next_action_at=None,
        resolved_at=None,
    )

    db.add(recovery_case)
    db.flush()

    return recovery_case


def seed_database() -> None:
    print("=" * 80)
    print("RAZORRECOVER AI — DATABASE SEED")
    print("=" * 80)

    print()
    print("1. Loading customer recovery queue...")

    if not QUEUE_PATH.exists():
        raise FileNotFoundError(
            f"Recovery queue not found: {QUEUE_PATH}"
        )

    queue = pd.read_parquet(QUEUE_PATH)

    if queue.empty:
        raise ValueError(
            "Customer recovery queue is empty."
        )

    print(f"   Queue rows: {len(queue):,}")

    required_columns = {
        "customer_id",
        "snapshot_date",
        "recovery_probability",
        "amount_at_risk",
    }

    missing = (
        required_columns
        - set(queue.columns)
    )

    if missing:
        raise ValueError(
            "Missing required columns: "
            + ", ".join(sorted(missing))
        )

    # We only need one current opportunity per customer.
    queue = (
        queue.sort_values(
            ["customer_id", "snapshot_date"]
        )
        .drop_duplicates(
            subset=["customer_id"],
            keep="last",
        )
        .copy()
    )

    queue = queue.sort_values(
        "expected_recovery_value",
        ascending=False,
    ).head(MAX_CASES)

    print(
        f"   Customers selected: {len(queue):,}"
    )

    print()
    print("2. Connecting to PostgreSQL...")

    db = SessionLocal()

    customers_created = 0
    transactions_created = 0
    cases_created = 0

    try:
        for _, row in queue.iterrows():
            customer_external_id = str(
                int(float(row["customer_id"]))
            )

            snapshot_date = pd.Timestamp(
                row["snapshot_date"]
            ).to_pydatetime()

            probability = float(
                row["recovery_probability"]
            )

            amount = float(
                row["amount_at_risk"]
            )

            if not 0 <= probability <= 1:
                raise ValueError(
                    f"Invalid recovery probability: "
                    f"{probability}"
                )

            if amount <= 0:
                continue

            amount_decimal = Decimal(
                str(round(amount, 2))
            )

            probability_decimal = Decimal(
                str(round(probability, 4))
            )

            customer_before = (
                db.query(Customer)
                .filter(
                    Customer.external_customer_id
                    == customer_external_id
                )
                .first()
            )

            customer = get_or_create_customer(
                db=db,
                customer_external_id=(
                    customer_external_id
                ),
                lifetime_value=amount_decimal,
                successful_payments=1,
            )

            if customer_before is None:
                customers_created += 1

            transaction_before = (
                db.query(Transaction)
                .filter(
                    Transaction.external_transaction_id
                    == (
                        f"recovery-seed-"
                        f"{customer_external_id}-"
                        f"{snapshot_date.strftime('%Y%m%d%H%M%S')}"
                    )
                )
                .first()
            )

            transaction = create_transaction(
                db=db,
                customer=customer,
                customer_external_id=(
                    customer_external_id
                ),
                snapshot_date=snapshot_date,
                amount=amount_decimal,
            )

            if transaction_before is None:
                transactions_created += 1

            case_before = (
                db.query(RecoveryCase)
                .filter(
                    RecoveryCase.transaction_id
                    == transaction.id
                )
                .first()
            )

            case = create_recovery_case(
                db=db,
                transaction=transaction,
                customer=customer,
                amount_at_risk=amount_decimal,
                recovery_probability=(
                    probability_decimal
                ),
            )

            if case_before is None and case is not None:
                cases_created += 1

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

    print()
    print("=" * 80)
    print("DATABASE SEED COMPLETE")
    print("=" * 80)

    print()
    print(
        f"Customers created:     {customers_created:,}"
    )
    print(
        f"Transactions created:  {transactions_created:,}"
    )
    print(
        f"Recovery cases created:{cases_created:,}"
    )

    print()
    print("Database is ready for API testing.")


if __name__ == "__main__":
    seed_database()