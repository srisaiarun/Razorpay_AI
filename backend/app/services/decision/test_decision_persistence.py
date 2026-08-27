from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.db.base import Base

from backend.app.models.agent_decision import AgentDecision
from backend.app.models.audit_log import AuditLog
from backend.app.models.customer import Customer
from backend.app.models.recovery_action import RecoveryAction
from backend.app.models.recovery_case import RecoveryCase
from backend.app.models.transaction import Transaction

from backend.app.services.decision.decision_persistence import (
    DecisionPersistenceService,
)


def main() -> None:

    print("=" * 80)
    print("RAZORRECOVER AI — DECISION + AUDIT PERSISTENCE TEST")
    print("=" * 80)

    # ---------------------------------------------------------
    # 1. Create isolated test database
    # ---------------------------------------------------------

    print()
    print("1. Creating isolated test database...")

    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
    )

    Base.metadata.create_all(engine)

    print(
        "   [PASS] Test database created"
    )

    # ---------------------------------------------------------
    # 2. Create test RecoveryCase
    # ---------------------------------------------------------

    print()
    print("2. Creating test recovery case...")

    with Session(engine) as db:

        customer = Customer(
            external_customer_id="TEST_CUSTOMER_001",
            name="Test Customer",
            email="test@example.com",
            lifetime_value=Decimal("5000.00"),
            successful_payments=10,
            failed_payments=1,
            opted_out=False,
        )

        db.add(customer)
        db.flush()

        transaction = Transaction(
            external_transaction_id=(
                "TEST_TRANSACTION_001"
            ),
            customer_id=customer.id,
            amount=Decimal("3710.74"),
            currency="GBP",
            status="FAILED",
            failure_reason="insufficient_funds",
            payment_method="card",
        )

        db.add(transaction)
        db.flush()

        recovery_case = RecoveryCase(
            transaction_id=transaction.id,
            customer_id=customer.id,
            amount_at_risk=Decimal("3710.74"),
            failure_class="INSUFFICIENT_FUNDS",
            risk_score=Decimal("0.7430"),
            recovery_probability=Decimal("0.7430"),
            status="OPEN",
            attempt_count=0,
        )

        db.add(recovery_case)
        db.commit()

        recovery_case_id = recovery_case.id

        print(
            f"   RecoveryCase ID: "
            f"{recovery_case_id}"
        )

    # ---------------------------------------------------------
    # 3. Run persistence service
    # ---------------------------------------------------------

    print()
    print("3. Running decision persistence service...")

    with Session(engine) as db:

        service = DecisionPersistenceService()

        agent_decision = (
            service.create_decision(
                db,
                recovery_case_id=recovery_case_id,
            )
        )

        db.commit()

        print(
            f"   AgentDecision ID: "
            f"{agent_decision.id}"
        )

        print(
            f"   Decision: "
            f"{agent_decision.decision}"
        )

        print(
            f"   Confidence: "
            f"{agent_decision.confidence}"
        )

        print(
            f"   Expected recovery: "
            f"£{agent_decision.expected_recovery_amount}"
        )

    # ---------------------------------------------------------
    # 4. Verify AgentDecision
    # ---------------------------------------------------------

    print()
    print("4. Verifying AgentDecision...")

    with Session(engine) as db:

        saved_decision = (
            db.query(AgentDecision)
            .filter(
                AgentDecision.recovery_case_id
                == recovery_case_id,
            )
            .first()
        )

        if saved_decision is None:
            raise AssertionError(
                "AgentDecision was not persisted."
            )

        if (
            saved_decision.decision
            != "HIGH_PRIORITY_RECOVERY"
        ):
            raise AssertionError(
                "Unexpected decision: "
                f"{saved_decision.decision}"
            )

        if saved_decision.policy_status != (
            "LOCKED_VALIDATION_POLICY"
        ):
            raise AssertionError(
                "Unexpected policy status: "
                f"{saved_decision.policy_status}"
            )

        if not saved_decision.requires_human_approval:
            raise AssertionError(
                "P1_HIGH decision should require "
                "human approval."
            )

        print(
            "   [PASS] AgentDecision persisted"
        )

        print(
            "   [PASS] Policy status verified"
        )

        print(
            "   [PASS] Human approval requirement verified"
        )

    # ---------------------------------------------------------
    # 5. Verify RecoveryAction
    # ---------------------------------------------------------

    print()
    print("5. Verifying RecoveryAction...")

    with Session(engine) as db:

        saved_decision = (
            db.query(AgentDecision)
            .filter(
                AgentDecision.recovery_case_id
                == recovery_case_id,
            )
            .first()
        )

        saved_action = (
            db.query(RecoveryAction)
            .filter(
                RecoveryAction.agent_decision_id
                == saved_decision.id,
            )
            .first()
        )

        if saved_action is None:
            raise AssertionError(
                "RecoveryAction was not persisted."
            )

        if (
            saved_action.action_type
            != "HIGH_PRIORITY_RECOVERY"
        ):
            raise AssertionError(
                "Unexpected action type: "
                f"{saved_action.action_type}"
            )

        if saved_action.status != (
            "PENDING_APPROVAL"
        ):
            raise AssertionError(
                "Unexpected action status: "
                f"{saved_action.status}"
            )

        if (
            saved_action.recovery_case_id
            != recovery_case_id
        ):
            raise AssertionError(
                "RecoveryAction is linked to "
                "the wrong RecoveryCase."
            )

        print(
            "   [PASS] RecoveryAction persisted"
        )

        print(
            "   [PASS] Action status verified"
        )

        print(
            "   [PASS] RecoveryCase relationship verified"
        )

    # ---------------------------------------------------------
    # 6. Verify AuditLog
    # ---------------------------------------------------------

    print()
    print("6. Verifying AuditLog...")

    with Session(engine) as db:

        audit = (
            db.query(AuditLog)
            .filter(
                AuditLog.recovery_case_id
                == recovery_case_id,
            )
            .first()
        )

        if audit is None:
            raise AssertionError(
                "AuditLog was not persisted."
            )

        if audit.event_type != (
            "AGENT_DECISION_CREATED"
        ):
            raise AssertionError(
                "Unexpected audit event type: "
                f"{audit.event_type}"
            )

        if audit.actor_type != "AI_AGENT":
            raise AssertionError(
                "Unexpected actor type: "
                f"{audit.actor_type}"
            )

        if audit.actor_id != (
            "recovery_decision_engine"
        ):
            raise AssertionError(
                "Unexpected actor ID: "
                f"{audit.actor_id}"
            )

        if audit.event_data is None:
            raise AssertionError(
                "Audit event_data is missing."
            )

        required_event_data = {
            "agent_decision_id",
            "recovery_action_id",
            "decision",
            "recovery_probability",
            "amount_at_risk",
            "expected_recovery_value",
            "recovery_risk_band",
            "priority_band",
            "priority_score",
            "policy_status",
            "requires_human_approval",
        }

        missing = (
            required_event_data
            - set(audit.event_data.keys())
        )

        if missing:
            raise AssertionError(
                "Audit event_data is missing fields: "
                f"{sorted(missing)}"
            )

        if (
            audit.event_data["decision"]
            != "HIGH_PRIORITY_RECOVERY"
        ):
            raise AssertionError(
                "Audit decision does not match "
                "AgentDecision."
            )

        if (
            audit.event_data["agent_decision_id"]
            <= 0
        ):
            raise AssertionError(
                "Invalid AgentDecision ID "
                "in audit event."
            )

        if (
            audit.event_data["recovery_action_id"]
            <= 0
        ):
            raise AssertionError(
                "Invalid RecoveryAction ID "
                "in audit event."
            )

        print(
            "   [PASS] AuditLog persisted"
        )

        print(
            "   [PASS] Actor metadata verified"
        )

        print(
            "   [PASS] Audit event data verified"
        )

    # ---------------------------------------------------------
    # 7. Final relationship verification
    # ---------------------------------------------------------

    print()
    print("7. Verifying complete decision chain...")

    with Session(engine) as db:

        decision = (
            db.query(AgentDecision)
            .filter(
                AgentDecision.recovery_case_id
                == recovery_case_id,
            )
            .first()
        )

        action = (
            db.query(RecoveryAction)
            .filter(
                RecoveryAction.agent_decision_id
                == decision.id,
            )
            .first()
        )

        audit = (
            db.query(AuditLog)
            .filter(
                AuditLog.recovery_case_id
                == recovery_case_id,
            )
            .first()
        )

        if action.agent_decision_id != decision.id:
            raise AssertionError(
                "Action → Decision relationship failed."
            )

        if action.recovery_case_id != (
            decision.recovery_case_id
        ):
            raise AssertionError(
                "Action → RecoveryCase relationship failed."
            )

        if audit.recovery_case_id != (
            decision.recovery_case_id
        ):
            raise AssertionError(
                "AuditLog → RecoveryCase relationship failed."
            )

        print(
            "   [PASS] RecoveryCase → AgentDecision"
        )

        print(
            "   [PASS] AgentDecision → RecoveryAction"
        )

        print(
            "   [PASS] RecoveryCase → AuditLog"
        )

    print()
    print("=" * 80)
    print("DECISION + AUDIT PERSISTENCE TEST PASSED")
    print("=" * 80)


if __name__ == "__main__":
    main()