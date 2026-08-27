from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.models.agent_decision import AgentDecision
from backend.app.models.recovery_action import RecoveryAction
from backend.app.services.decision.decision_persistence import (
    DecisionPersistenceService,
)


router = APIRouter(
    prefix="/api/v1/recovery-cases",
    tags=["Recovery Cases"],
)


def get_db():
    """
    Provide a SQLAlchemy database session for one request.

    The API owns the transaction lifecycle:
        request
          ↓
        database session
          ↓
        commit / rollback
          ↓
        close
    """

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


class RecoveryDecisionResponse(BaseModel):
    recovery_case_id: int

    agent_decision_id: int

    recovery_action_id: int

    decision: str

    reasoning_summary: str

    confidence: float

    expected_recovery_amount: float

    policy_status: str

    requires_human_approval: bool

    action_type: str

    action_status: str

    amount: float

    created_at: datetime


@router.post(
    "/{recovery_case_id}/decide",
    response_model=RecoveryDecisionResponse,
    status_code=status.HTTP_200_OK,
)
def create_recovery_decision(
    recovery_case_id: int,
    db: Session = Depends(get_db),
):
    """
    Run the deterministic recovery decision engine for
    an existing RecoveryCase and persist the resulting:

        AgentDecision
        RecoveryAction
        AuditLog

    The complete operation is committed atomically.
    """

    persistence_service = DecisionPersistenceService()

    try:
        agent_decision = (
            persistence_service.create_decision(
                db,
                recovery_case_id=recovery_case_id,
            )
        )

        db.commit()

        db.refresh(agent_decision)

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Failed to create recovery decision."
            ),
        ) from exc

    recovery_action = (
        db.query(RecoveryAction)
        .filter(
            RecoveryAction.agent_decision_id
            == agent_decision.id
        )
        .first()
    )

    if recovery_action is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Recovery action was not created "
                "for the agent decision."
            ),
        )

    return RecoveryDecisionResponse(
        recovery_case_id=agent_decision.recovery_case_id,
        agent_decision_id=agent_decision.id,
        recovery_action_id=recovery_action.id,
        decision=agent_decision.decision,
        reasoning_summary=agent_decision.reasoning_summary,
        confidence=float(agent_decision.confidence),
        expected_recovery_amount=float(
            agent_decision.expected_recovery_amount
        ),
        policy_status=agent_decision.policy_status,
        requires_human_approval=(
            agent_decision.requires_human_approval
        ),
        action_type=recovery_action.action_type,
        action_status=recovery_action.status,
        amount=float(recovery_action.amount),
        created_at=agent_decision.created_at,
    )