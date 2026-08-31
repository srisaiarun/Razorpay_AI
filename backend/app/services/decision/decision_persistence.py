from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from backend.app.models.agent_decision import AgentDecision
from backend.app.models.audit_log import AuditLog
from backend.app.models.recovery_action import RecoveryAction
from backend.app.models.recovery_case import RecoveryCase

from backend.app.services.decision.decision_engine import DecisionEngine


class DecisionPersistenceService:
    """
    Runs the deterministic recovery decision engine and persists
    the resulting AgentDecision, RecoveryAction, and AuditLog.

    The caller owns the SQLAlchemy transaction.
    This service does not commit automatically.
    """

    ACTOR_TYPE = "AI_AGENT"
    ACTOR_ID = "recovery_decision_engine"
    POLICY_STATUS = "LOCKED_VALIDATION_POLICY"

    def __init__(
        self,
        decision_engine: DecisionEngine | None = None,
    ) -> None:
        self.engine = (
            decision_engine
            if decision_engine is not None
            else DecisionEngine()
        )

    def create_decision(
        self,
        db: Session,
        *,
        recovery_case_id: int,
    ) -> AgentDecision:
        """
        Create and persist:

            AgentDecision
                ↓
            RecoveryAction
                ↓
            AuditLog

        All records are added to the same SQLAlchemy transaction.
        """

        # ---------------------------------------------------------
        # 1. Load RecoveryCase
        # ---------------------------------------------------------

        recovery_case = (
            db.query(RecoveryCase)
            .filter(
                RecoveryCase.id == recovery_case_id,
            )
            .first()
        )

        if recovery_case is None:
            raise ValueError(
                f"RecoveryCase {recovery_case_id} does not exist."
            )

        if recovery_case.recovery_probability is None:
            raise ValueError(
                f"RecoveryCase {recovery_case_id} "
                "does not have a recovery probability."
            )

        # ---------------------------------------------------------
        # 2. Run decision engine
        # ---------------------------------------------------------

        decision = self.engine.decide(
            customer_id=recovery_case.customer_id,
            recovery_probability=float(
                recovery_case.recovery_probability,
            ),
            amount_at_risk=float(
                recovery_case.amount_at_risk,
            ),
            snapshot_date=None,
        )

        # ---------------------------------------------------------
        # 3. Keep RecoveryCase probability synchronized
        # ---------------------------------------------------------

        recovery_case.recovery_probability = Decimal(
            str(
                round(
                    decision.recovery_probability,
                    4,
                )
            )
        )

        # ---------------------------------------------------------
        # 4. Determine human approval requirement
        # ---------------------------------------------------------

        requires_human_approval = (
            decision.priority_band == "P1_HIGH"
        )

        # ---------------------------------------------------------
        # 5. Create AgentDecision
        # ---------------------------------------------------------

        agent_decision = AgentDecision(
            recovery_case_id=recovery_case.id,
            decision=decision.recommended_action,
            reasoning_summary=decision.decision_reason,
            confidence=Decimal(
                str(
                    round(
                        decision.recovery_probability,
                        4,
                    )
                )
            ),
            expected_recovery_amount=Decimal(
                str(
                    round(
                        decision.expected_recovery_value,
                        2,
                    )
                )
            ),
            policy_status=self.POLICY_STATUS,
            requires_human_approval=(
                requires_human_approval
            ),
        )

        db.add(agent_decision)

        # We need the generated AgentDecision ID before
        # creating RecoveryAction.
        db.flush()

        # ---------------------------------------------------------
        # 6. Create RecoveryAction
        # ---------------------------------------------------------

        action_status = self._action_status(
            decision.recommended_action,
            requires_human_approval,
        )

        recovery_action = RecoveryAction(
            recovery_case_id=recovery_case.id,
            agent_decision_id=agent_decision.id,
            action_type=decision.recommended_action,
            status=action_status,
            amount=Decimal(
                str(
                    round(
                        decision.expected_recovery_value,
                        2,
                    )
                )
            ),
            external_reference=None,
            failure_reason=None,
            attempt_number=(
                recovery_case.attempt_count + 1
            ),
        )

        db.add(recovery_action)

        db.flush()

        # ---------------------------------------------------------
        # 7. Create AuditLog
        # ---------------------------------------------------------

        audit_log = AuditLog(
            recovery_case_id=recovery_case.id,
            event_type="AGENT_DECISION_CREATED",
            actor_type=self.ACTOR_TYPE,
            actor_id=self.ACTOR_ID,
            message="AI recovery decision created.",
            event_data={
                "agent_decision_id": agent_decision.id,
                "recovery_action_id": recovery_action.id,
                "decision": decision.recommended_action,
                "recovery_probability": round(
                    decision.recovery_probability,
                    4,
                ),
                "amount_at_risk": round(
                    decision.amount_at_risk,
                    2,
                ),
                "expected_recovery_value": round(
                    decision.expected_recovery_value,
                    2,
                ),
                "recovery_risk_band": (
                    decision.recovery_risk_band
                ),
                "priority_band": decision.priority_band,
                "priority_score": round(
                    decision.priority_score,
                    2,
                ),
                "policy_status": self.POLICY_STATUS,
                "requires_human_approval": (
                    requires_human_approval
                ),
            },
        )

        db.add(audit_log)

        db.flush()

        return agent_decision

    @staticmethod
    def _action_status(
        action: str,
        requires_human_approval: bool,
    ) -> str:
        """
        Convert a decision-engine action into an
        operational RecoveryAction status.

        Human approval is determined by the decision policy.
        This method only translates that decision into an
        operational execution state.

        State mapping:

            NO_ACTION
                -> SKIPPED

            MONITOR
                -> PENDING

            LOW_COST_RECOVERY
                -> PENDING

            STANDARD_RECOVERY
                -> PENDING

            HIGH_PRIORITY_RECOVERY
                -> PENDING_APPROVAL
                   when human approval is required

            Any executable recovery action
                -> PENDING
                   when human approval is not required
        """

        # No recovery action should be executed.
        if action == "NO_ACTION":
            return "SKIPPED"

        # Monitoring is not an immediate execution action.
        if action == "MONITOR":
            return "PENDING"

        executable_actions = {
            "LOW_COST_RECOVERY",
            "STANDARD_RECOVERY",
            "HIGH_PRIORITY_RECOVERY",
        }

        if action not in executable_actions:
            raise ValueError(
                f"Unknown recovery action: {action}"
            )

        if requires_human_approval:
            return "PENDING_APPROVAL"

        return "PENDING"


def decision_to_dict(
    decision: AgentDecision,
) -> dict[str, Any]:
    """
    Convert AgentDecision into a JSON-friendly dictionary.
    """

    return {
        "id": decision.id,
        "recovery_case_id": decision.recovery_case_id,
        "decision": decision.decision,
        "reasoning_summary": decision.reasoning_summary,
        "confidence": float(
            decision.confidence
        ),
        "expected_recovery_amount": float(
            decision.expected_recovery_amount
        ),
        "policy_status": decision.policy_status,
        "requires_human_approval": (
            decision.requires_human_approval
        ),
        "created_at": decision.created_at,
    }