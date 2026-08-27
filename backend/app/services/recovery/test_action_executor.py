from __future__ import annotations

from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.db.base import Base
from backend.app.models.agent_decision import AgentDecision
from backend.app.models.audit_log import AuditLog
from backend.app.models.customer import Customer
from backend.app.models.recovery_action import RecoveryAction
from backend.app.models.recovery_case import RecoveryCase
from backend.app.models.transaction import Transaction
from backend.app.services.recovery.action_executor import (
    RecoveryActionExecutor,
)


def create_test_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={
            "check_same_thread": False,
        },
    )

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    Base.metadata.create_all(engine)

    return engine, TestingSessionLocal


def main() -> None:
    print("=" * 80)
    print("RAZORRECOVER AI — RECOVERY ACTION EXECUTOR TEST")
    print("=" * 80)

    engine, TestingSessionLocal = create_test_session()
    db = TestingSessionLocal()

    try:
        print()
        print("1. Creating isolated test database...")
        print("   [PASS] Test database created")

        # =====================================================
        # TEST A — Successful execution
        # =====================================================

        print()
        print("2. Creating executable recovery case...")

        customer = Customer(
            external_customer_id="executor_test_customer_001",
            name="Executor Test Customer",
            email="executor-test@example.com",
            lifetime_value=5000,
            successful_payments=5,
            failed_payments=1,
            opted_out=False,
        )

        db.add(customer)
        db.flush()

        transaction = Transaction(
            external_transaction_id=(
                "executor_test_transaction_001"
            ),
            customer_id=customer.id,
            amount=Decimal("1000.00"),
            currency="INR",
            status="FAILED",
            failure_reason="TEST_FAILURE",
            payment_method="card",
        )

        db.add(transaction)
        db.flush()

        recovery_case = RecoveryCase(
            transaction_id=transaction.id,
            customer_id=customer.id,
            amount_at_risk=Decimal("1000.00"),
            failure_class="TEST_FAILURE",
            risk_score=Decimal("0.5000"),
            recovery_probability=Decimal("0.6000"),
            status="OPEN",
            attempt_count=0,
        )

        db.add(recovery_case)
        db.flush()

        agent_decision = AgentDecision(
            recovery_case_id=recovery_case.id,
            decision="LOW_COST_RECOVERY",
            reasoning_summary="Test recovery decision.",
            confidence=Decimal("0.6000"),
            expected_recovery_amount=Decimal("600.00"),
            policy_status="LOCKED_VALIDATION_POLICY",
            requires_human_approval=False,
        )

        db.add(agent_decision)
        db.flush()

        action = RecoveryAction(
            recovery_case_id=recovery_case.id,
            agent_decision_id=agent_decision.id,
            action_type="LOW_COST_RECOVERY",
            status="PENDING",
            amount=Decimal("600.00"),
            attempt_number=1,
        )

        db.add(action)
        db.commit()

        print(
            f"   RecoveryAction ID: {action.id}"
        )

        # =====================================================
        # Execute successful action
        # =====================================================

        print()
        print("3. Executing PENDING action...")

        executor = RecoveryActionExecutor()

        executed_action = executor.execute(
            db,
            action_id=action.id,
        )

        db.commit()

        print(
            f"   Final action status: "
            f"{executed_action.status}"
        )

        # =====================================================
        # Verify action
        # =====================================================

        print()
        print("4. Verifying successful execution...")

        db.refresh(executed_action)

        assert executed_action.status == "COMPLETED"

        assert (
            executed_action.completed_at
            is not None
        )

        print(
            "   [PASS] Action marked COMPLETED"
        )

        print(
            "   [PASS] completed_at populated"
        )

        # =====================================================
        # Verify recovery case
        # =====================================================

        db.refresh(recovery_case)

        assert recovery_case.status == "RECOVERED"

        assert (
            recovery_case.resolved_at
            is not None
        )

        assert recovery_case.next_action_at is None

        assert recovery_case.attempt_count == 1

        print(
            "   [PASS] RecoveryCase marked RECOVERED"
        )

        print(
            "   [PASS] resolved_at populated"
        )

        print(
            "   [PASS] attempt count incremented"
        )

        # =====================================================
        # Verify execution audit
        # =====================================================

        print()
        print("5. Verifying execution audit...")

        execution_audit = (
            db.query(AuditLog)
            .filter(
                AuditLog.recovery_case_id
                == recovery_case.id,
                AuditLog.event_type
                == "RECOVERY_ACTION_EXECUTED",
            )
            .first()
        )

        assert execution_audit is not None

        assert (
            execution_audit.actor_type
            == "RECOVERY_EXECUTOR"
        )

        assert (
            execution_audit.actor_id
            == "recovery_action_executor"
        )

        assert execution_audit.event_data is not None

        assert (
            execution_audit.event_data[
                "execution_mode"
            ]
            == "SIMULATED"
        )

        print(
            "   [PASS] Execution audit persisted"
        )

        print(
            "   [PASS] Actor metadata verified"
        )

        print(
            "   [PASS] Execution metadata verified"
        )

        # =====================================================
        # Duplicate execution protection
        # =====================================================

        print()
        print(
            "6. Testing duplicate execution protection..."
        )

        try:
            executor.execute(
                db,
                action_id=action.id,
            )

            raise AssertionError(
                "Completed action was executed twice."
            )

        except ValueError as exc:
            assert (
                "already been completed"
                in str(exc)
            )

        db.rollback()

        print(
            "   [PASS] Completed action cannot execute twice"
        )

        # =====================================================
        # TEST B — Approval protection
        # =====================================================

        print()
        print(
            "7. Creating approval-required action..."
        )

        customer_2 = Customer(
            external_customer_id="executor_test_customer_002",
            name="Approval Test Customer",
            email="approval-test@example.com",
            lifetime_value=5000,
            successful_payments=5,
            failed_payments=1,
            opted_out=False,
        )

        db.add(customer_2)
        db.flush()

        transaction_2 = Transaction(
            external_transaction_id=(
                "executor_test_transaction_002"
            ),
            customer_id=customer_2.id,
            amount=Decimal("2000.00"),
            currency="INR",
            status="FAILED",
            failure_reason="TEST_APPROVAL",
            payment_method="card",
        )

        db.add(transaction_2)
        db.flush()

        case_2 = RecoveryCase(
            transaction_id=transaction_2.id,
            customer_id=customer_2.id,
            amount_at_risk=Decimal("2000.00"),
            failure_class="TEST_APPROVAL",
            risk_score=Decimal("0.7000"),
            recovery_probability=Decimal("0.7500"),
            status="OPEN",
            attempt_count=0,
        )

        db.add(case_2)
        db.flush()

        decision_2 = AgentDecision(
            recovery_case_id=case_2.id,
            decision="STANDARD_RECOVERY",
            reasoning_summary=(
                "Human approval required."
            ),
            confidence=Decimal("0.7500"),
            expected_recovery_amount=Decimal("1500.00"),
            policy_status="LOCKED_VALIDATION_POLICY",
            requires_human_approval=True,
        )

        db.add(decision_2)
        db.flush()

        approval_action = RecoveryAction(
            recovery_case_id=case_2.id,
            agent_decision_id=decision_2.id,
            action_type="STANDARD_RECOVERY",
            status="PENDING_APPROVAL",
            amount=Decimal("1500.00"),
            attempt_number=1,
        )

        db.add(approval_action)
        db.commit()

        print(
            f"   Approval action ID: "
            f"{approval_action.id}"
        )

        # =====================================================
        # Attempt unauthorized execution
        # =====================================================

        print()
        print(
            "8. Testing human-approval protection..."
        )

        try:
            executor.execute(
                db,
                action_id=approval_action.id,
            )

            raise AssertionError(
                "Approval-required action executed."
            )

        except PermissionError as exc:
            assert (
                "requires human approval"
                in str(exc)
            )

            # The executor created an audit record before
            # raising PermissionError.
            db.commit()

        db.refresh(approval_action)
        db.refresh(case_2)

        assert (
            approval_action.status
            == "PENDING_APPROVAL"
        )

        assert case_2.status == "OPEN"

        assert case_2.attempt_count == 0

        print(
            "   [PASS] Approval-required action blocked"
        )

        print(
            "   [PASS] Action status unchanged"
        )

        print(
            "   [PASS] RecoveryCase remains OPEN"
        )

        print(
            "   [PASS] Attempt count unchanged"
        )

        # =====================================================
        # Verify blocked audit
        # =====================================================

        print()
        print(
            "9. Verifying blocked-execution audit..."
        )

        blocked_audit = (
            db.query(AuditLog)
            .filter(
                AuditLog.recovery_case_id
                == case_2.id,
                AuditLog.event_type
                == "RECOVERY_ACTION_BLOCKED",
            )
            .first()
        )

        assert blocked_audit is not None

        assert (
            blocked_audit.actor_type
            == "RECOVERY_EXECUTOR"
        )

        assert (
            blocked_audit.actor_id
            == "recovery_action_executor"
        )

        assert blocked_audit.event_data is not None

        assert (
            blocked_audit.event_data["status"]
            == "PENDING_APPROVAL"
        )

        print(
            "   [PASS] Blocked execution audit persisted"
        )

        print(
            "   [PASS] Block reason recorded"
        )

        # =====================================================
        # Complete test
        # =====================================================

        print()
        print("=" * 80)
        print(
            "RECOVERY ACTION EXECUTOR TEST PASSED"
        )
        print("=" * 80)

    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    main()