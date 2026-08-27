from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.models.audit_log import AuditLog
from backend.app.models.recovery_action import RecoveryAction
from backend.app.models.recovery_case import RecoveryCase


class RecoveryActionExecutor:
    """
    Safely executes RecoveryAction records.

    This implementation is provider-independent and simulated.

    It does NOT:
        - call Razorpay
        - initiate refunds
        - charge customers
        - move real money

    It only simulates execution while maintaining database state,
    enforcing approval requirements, and creating audit records.
    """

    ACTOR_TYPE = "RECOVERY_EXECUTOR"
    ACTOR_ID = "recovery_action_executor"

    APPROVER_ACTOR_TYPE = "HUMAN_APPROVER"

    EXECUTABLE_STATUSES = {
        "PENDING",
    }

    TERMINAL_STATUSES = {
        "COMPLETED",
        "FAILED",
        "SKIPPED",
    }

    BLOCKED_STATUSES = {
        "PENDING_APPROVAL",
    }

    # ------------------------------------------------------------------
    # EXECUTION
    # ------------------------------------------------------------------

    def execute(
        self,
        db: Session,
        *,
        action_id: int,
    ) -> RecoveryAction:
        """
        Execute a recovery action.

        State transitions:

            PENDING
                -> COMPLETED

            PENDING_APPROVAL
                -> rejected / unchanged

            SKIPPED
                -> rejected / unchanged

            COMPLETED
                -> rejected / unchanged

            FAILED
                -> rejected / unchanged
        """

        # --------------------------------------------------------------
        # 1. Load action
        # --------------------------------------------------------------

        action = (
            db.query(RecoveryAction)
            .filter(
                RecoveryAction.id == action_id,
            )
            .first()
        )

        if action is None:
            raise ValueError(
                f"RecoveryAction {action_id} does not exist."
            )

        # --------------------------------------------------------------
        # 2. Load recovery case
        # --------------------------------------------------------------

        recovery_case = (
            db.query(RecoveryCase)
            .filter(
                RecoveryCase.id == action.recovery_case_id,
            )
            .first()
        )

        if recovery_case is None:
            raise ValueError(
                f"RecoveryCase {action.recovery_case_id} "
                "does not exist."
            )

        # --------------------------------------------------------------
        # 3. Enforce action state
        # --------------------------------------------------------------

        if action.status == "PENDING_APPROVAL":
            reason = (
                "Recovery action requires human approval "
                "before execution."
            )

            self._audit_blocked(
                db=db,
                action=action,
                recovery_case=recovery_case,
                reason=reason,
            )

            raise PermissionError(
                f"RecoveryAction {action_id} "
                "requires human approval before execution."
            )

        if action.status == "SKIPPED":
            raise ValueError(
                f"RecoveryAction {action_id} "
                "is marked SKIPPED and cannot be executed."
            )

        if action.status == "COMPLETED":
            raise ValueError(
                f"RecoveryAction {action_id} "
                "has already been completed."
            )

        if action.status == "FAILED":
            raise ValueError(
                f"RecoveryAction {action_id} "
                "has failed and cannot be executed again "
                "without an explicit retry workflow."
            )

        if action.status != "PENDING":
            raise ValueError(
                f"RecoveryAction {action_id} has unsupported "
                f"status '{action.status}'."
            )

        # --------------------------------------------------------------
        # 4. Validate recovery case
        # --------------------------------------------------------------

        if recovery_case.status != "OPEN":
            raise ValueError(
                f"RecoveryCase {recovery_case.id} "
                f"is not OPEN. Current status: "
                f"{recovery_case.status}"
            )

        if action.amount <= Decimal("0"):
            raise ValueError(
                f"RecoveryAction {action_id} "
                "must have a positive amount."
            )

        # --------------------------------------------------------------
        # 5. Simulated execution
        # --------------------------------------------------------------

        now = datetime.utcnow()

        action.status = "COMPLETED"
        action.completed_at = now

        recovery_case.status = "RECOVERED"
        recovery_case.resolved_at = now

        recovery_case.attempt_count = (
            recovery_case.attempt_count + 1
        )

        recovery_case.next_action_at = None

        db.flush()

        # --------------------------------------------------------------
        # 6. Audit successful execution
        # --------------------------------------------------------------

        audit_log = AuditLog(
            recovery_case_id=recovery_case.id,
            event_type="RECOVERY_ACTION_EXECUTED",
            actor_type=self.ACTOR_TYPE,
            actor_id=self.ACTOR_ID,
            message=(
                "Recovery action executed successfully "
                "in simulated execution mode."
            ),
            event_data={
                "recovery_action_id": action.id,
                "agent_decision_id": action.agent_decision_id,
                "action_type": action.action_type,
                "status": action.status,
                "amount": float(action.amount),
                "attempt_number": action.attempt_number,
                "execution_mode": "SIMULATED",
            },
        )

        db.add(audit_log)
        db.flush()

        return action

    # ------------------------------------------------------------------
    # HUMAN APPROVAL
    # ------------------------------------------------------------------

    def approve(
        self,
        db: Session,
        *,
        action_id: int,
        approver_id: str,
        approval_reason: str | None = None,
    ) -> RecoveryAction:
        """
        Approve a recovery action that requires human approval.

        State transition:

            PENDING_APPROVAL
                -> PENDING

        The action is NOT executed here.

        This method only authorizes the action for a later
        execution request.
        """

        # --------------------------------------------------------------
        # 1. Validate approver
        # --------------------------------------------------------------

        approver_id = approver_id.strip()

        if not approver_id:
            raise ValueError(
                "approver_id must not be empty."
            )

        if len(approver_id) > 100:
            raise ValueError(
                "approver_id must be at most 100 characters."
            )

        # --------------------------------------------------------------
        # 2. Load action
        # --------------------------------------------------------------

        action = (
            db.query(RecoveryAction)
            .filter(
                RecoveryAction.id == action_id,
            )
            .first()
        )

        if action is None:
            raise ValueError(
                f"RecoveryAction {action_id} does not exist."
            )

        # --------------------------------------------------------------
        # 3. Load recovery case
        # --------------------------------------------------------------

        recovery_case = (
            db.query(RecoveryCase)
            .filter(
                RecoveryCase.id == action.recovery_case_id,
            )
            .first()
        )

        if recovery_case is None:
            raise ValueError(
                f"RecoveryCase {action.recovery_case_id} "
                "does not exist."
            )

        # --------------------------------------------------------------
        # 4. Enforce approval state
        # --------------------------------------------------------------

        if action.status == "PENDING":
            raise ValueError(
                f"RecoveryAction {action_id} "
                "has already been approved."
            )

        if action.status == "COMPLETED":
            raise ValueError(
                f"RecoveryAction {action_id} "
                "has already been completed."
            )

        if action.status == "SKIPPED":
            raise ValueError(
                f"RecoveryAction {action_id} "
                "is marked SKIPPED and cannot be approved."
            )

        if action.status == "FAILED":
            raise ValueError(
                f"RecoveryAction {action_id} "
                "has failed and cannot be approved."
            )

        if action.status != "PENDING_APPROVAL":
            raise ValueError(
                f"RecoveryAction {action_id} has unsupported "
                f"status '{action.status}'."
            )

        # --------------------------------------------------------------
        # 5. Validate recovery case
        # --------------------------------------------------------------

        if recovery_case.status != "OPEN":
            raise ValueError(
                f"RecoveryCase {recovery_case.id} "
                f"is not OPEN. Current status: "
                f"{recovery_case.status}"
            )

        # --------------------------------------------------------------
        # 6. Approve action
        # --------------------------------------------------------------

        action.status = "PENDING"

        db.flush()

        # --------------------------------------------------------------
        # 7. Audit approval
        # --------------------------------------------------------------

        audit_log = AuditLog(
            recovery_case_id=recovery_case.id,
            event_type="RECOVERY_ACTION_APPROVED",
            actor_type=self.APPROVER_ACTOR_TYPE,
            actor_id=approver_id,
            message=(
                "Recovery action approved by human reviewer."
            ),
            event_data={
                "recovery_action_id": action.id,
                "agent_decision_id": action.agent_decision_id,
                "action_type": action.action_type,
                "previous_status": "PENDING_APPROVAL",
                "new_status": "PENDING",
                "approval_reason": approval_reason,
            },
        )

        db.add(audit_log)
        db.flush()

        return action

    # ------------------------------------------------------------------
    # BLOCKED EXECUTION AUDIT
    # ------------------------------------------------------------------

    def _audit_blocked(
        self,
        db: Session,
        *,
        action: RecoveryAction,
        recovery_case: RecoveryCase,
        reason: str,
    ) -> None:
        """
        Record an attempted execution that was blocked by policy.
        """

        audit_log = AuditLog(
            recovery_case_id=recovery_case.id,
            event_type="RECOVERY_ACTION_BLOCKED",
            actor_type=self.ACTOR_TYPE,
            actor_id=self.ACTOR_ID,
            message=reason,
            event_data={
                "recovery_action_id": action.id,
                "agent_decision_id": action.agent_decision_id,
                "action_type": action.action_type,
                "status": action.status,
                "reason": reason,
            },
        )

        db.add(audit_log)
        db.flush()


def recovery_action_to_dict(
    action: RecoveryAction,
) -> dict:
    """
    Convert RecoveryAction to a JSON-friendly dictionary.
    """

    return {
        "id": action.id,
        "recovery_case_id": action.recovery_case_id,
        "agent_decision_id": action.agent_decision_id,
        "action_type": action.action_type,
        "status": action.status,
        "amount": float(action.amount),
        "external_reference": action.external_reference,
        "failure_reason": action.failure_reason,
        "attempt_number": action.attempt_number,
        "created_at": action.created_at,
        "completed_at": action.completed_at,
    }