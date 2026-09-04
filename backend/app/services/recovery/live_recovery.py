from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.ml.live_features import build_customer_features
from backend.app.ml.recovery_predictor import recovery_predictor
from backend.app.models.customer import Customer
from backend.app.models.recovery_case import RecoveryCase
from backend.app.models.transaction import Transaction
from backend.app.services.decision.decision_persistence import (
    DecisionPersistenceService,
)


class LiveRecoveryService:
    """
    Production-style orchestration for a failed Razorpay payment.

    Flow:

        Failed Transaction
            ↓
        Live Customer Features
            ↓
        ML Recovery Probability
            ↓
        RecoveryCase
            ↓
        Deterministic Decision Engine
            ↓
        AgentDecision
            ↓
        RecoveryAction
            ↓
        AuditLog

    The caller owns the database transaction.
    """

    def __init__(
        self,
        decision_persistence: DecisionPersistenceService | None = None,
    ) -> None:
        self.decision_persistence = (
            decision_persistence
            if decision_persistence is not None
            else DecisionPersistenceService()
        )

    def process_failed_transaction(
        self,
        db: Session,
        *,
        transaction: Transaction,
    ) -> RecoveryCase:
        """
        Run ML + recovery decisioning for a failed transaction.

        Idempotent at the RecoveryCase level because
        RecoveryCase.transaction_id is unique.
        """

        if transaction.status.upper() != "FAILED":
            raise ValueError(
                f"Transaction {transaction.id} is not FAILED."
            )

        # ---------------------------------------------------------
        # 1. Existing RecoveryCase
        # ---------------------------------------------------------

        existing_case = (
            db.query(RecoveryCase)
            .filter(
                RecoveryCase.transaction_id
                == transaction.id,
            )
            .first()
        )

        if existing_case is not None:
            return existing_case

        # ---------------------------------------------------------
        # 2. Load customer
        # ---------------------------------------------------------

        customer = (
            db.query(Customer)
            .filter(
                Customer.id == transaction.customer_id,
            )
            .first()
        )

        if customer is None:
            raise ValueError(
                f"Customer {transaction.customer_id} "
                "does not exist."
            )

        # ---------------------------------------------------------
        # 3. Build live features
        # ---------------------------------------------------------

        snapshot_date = transaction.created_at

        features = build_customer_features(
            db,
            customer,
            snapshot_date,
        )

        # ---------------------------------------------------------
        # 4. ML prediction
        # ---------------------------------------------------------

        prediction = recovery_predictor.predict(
            features
        )

        recovery_probability = float(
            prediction["recovery_probability"]
        )

        if not 0.0 <= recovery_probability <= 1.0:
            raise ValueError(
                "ML recovery probability is outside [0, 1]."
            )

        # ---------------------------------------------------------
        # 5. Create RecoveryCase
        # ---------------------------------------------------------

        amount_at_risk = Decimal(
            str(
                round(
                    float(transaction.amount),
                    2,
                )
            )
        )

        risk_score = Decimal(
            str(
                round(
                    1.0 - recovery_probability,
                    4,
                )
            )
        )

        recovery_probability_decimal = Decimal(
            str(
                round(
                    recovery_probability,
                    4,
                )
            )
        )

        recovery_case = RecoveryCase(
            transaction_id=transaction.id,
            customer_id=customer.id,
            amount_at_risk=amount_at_risk,
            failure_class=(
                transaction.failure_reason
                or "PAYMENT_FAILURE"
            ),
            risk_score=risk_score,
            recovery_probability=(
                recovery_probability_decimal
            ),
            status="OPEN",
            attempt_count=0,
            next_action_at=None,
            created_at=datetime.utcnow(),
            resolved_at=None,
        )

        db.add(recovery_case)
        db.flush()

        # ---------------------------------------------------------
        # 6. Create AgentDecision + RecoveryAction + AuditLog
        # ---------------------------------------------------------

        self.decision_persistence.create_decision(
            db,
            recovery_case_id=recovery_case.id,
        )

        db.flush()

        return recovery_case