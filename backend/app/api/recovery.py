from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.models.agent_decision import AgentDecision
from backend.app.models.audit_log import AuditLog
from backend.app.models.recovery_action import RecoveryAction
from backend.app.models.recovery_case import RecoveryCase
from backend.app.services.decision.decision_persistence import (
    DecisionPersistenceService,
)
from backend.app.services.recovery.action_executor import (
    recovery_action_to_dict,
)


router = APIRouter(
    prefix="/api/v1/recovery-cases",
    tags=["Recovery Cases"],
)


def get_db():
    """
    Provide a SQLAlchemy database session for one request.
    """

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================


class RecoveryCaseResponse(BaseModel):
    id: int
    transaction_id: int
    customer_id: int
    amount_at_risk: float
    failure_class: str
    risk_score: float
    recovery_probability: float | None
    status: str
    attempt_count: int
    next_action_at: datetime | None
    created_at: datetime
    resolved_at: datetime | None


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


class RecoveryActionResponse(BaseModel):
    id: int
    recovery_case_id: int
    agent_decision_id: int
    action_type: str
    status: str
    amount: float
    external_reference: str | None
    failure_reason: str | None
    attempt_number: int
    created_at: datetime
    completed_at: datetime | None


class AuditLogResponse(BaseModel):
    id: int
    recovery_case_id: int | None
    event_type: str
    actor_type: str
    actor_id: str | None
    message: str
    event_data: dict | None
    created_at: datetime


# ============================================================================
# CREATE DECISION
# ============================================================================


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
    Run the deterministic recovery decision engine and persist:

        AgentDecision
        RecoveryAction
        AuditLog

    The complete operation is committed atomically.
    """

    persistence_service = DecisionPersistenceService()

    try:
        agent_decision = persistence_service.create_decision(
            db,
            recovery_case_id=recovery_case_id,
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
            detail="Failed to create recovery decision.",
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


# ============================================================================
# GET RECOVERY CASE
# ============================================================================


@router.get(
    "/{recovery_case_id}",
    response_model=RecoveryCaseResponse,
    status_code=status.HTTP_200_OK,
)
def get_recovery_case(
    recovery_case_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve the current state of a recovery case.
    """

    recovery_case = (
        db.query(RecoveryCase)
        .filter(
            RecoveryCase.id == recovery_case_id,
        )
        .first()
    )

    if recovery_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"RecoveryCase {recovery_case_id} "
                "does not exist."
            ),
        )

    return RecoveryCaseResponse(
        id=recovery_case.id,
        transaction_id=recovery_case.transaction_id,
        customer_id=recovery_case.customer_id,
        amount_at_risk=float(recovery_case.amount_at_risk),
        failure_class=recovery_case.failure_class,
        risk_score=float(recovery_case.risk_score),
        recovery_probability=(
            float(recovery_case.recovery_probability)
            if recovery_case.recovery_probability is not None
            else None
        ),
        status=recovery_case.status,
        attempt_count=recovery_case.attempt_count,
        next_action_at=recovery_case.next_action_at,
        created_at=recovery_case.created_at,
        resolved_at=recovery_case.resolved_at,
    )


# ============================================================================
# GET LATEST DECISION
# ============================================================================


@router.get(
    "/{recovery_case_id}/decision",
    response_model=RecoveryDecisionResponse,
    status_code=status.HTTP_200_OK,
)
def get_recovery_decision(
    recovery_case_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve the latest persisted decision and its associated action.
    """

    recovery_case = (
        db.query(RecoveryCase)
        .filter(
            RecoveryCase.id == recovery_case_id,
        )
        .first()
    )

    if recovery_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"RecoveryCase {recovery_case_id} "
                "does not exist."
            ),
        )

    agent_decision = (
        db.query(AgentDecision)
        .filter(
            AgentDecision.recovery_case_id
            == recovery_case_id
        )
        .order_by(
            AgentDecision.id.desc()
        )
        .first()
    )

    if agent_decision is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No decision exists for "
                f"RecoveryCase {recovery_case_id}."
            ),
        )

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
                "Recovery action was not found "
                "for the latest agent decision."
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


# ============================================================================
# GET ACTIONS
# ============================================================================


@router.get(
    "/{recovery_case_id}/actions",
    response_model=list[RecoveryActionResponse],
    status_code=status.HTTP_200_OK,
)
def get_recovery_actions(
    recovery_case_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve all recovery actions for a recovery case.
    """

    recovery_case = (
        db.query(RecoveryCase)
        .filter(
            RecoveryCase.id == recovery_case_id,
        )
        .first()
    )

    if recovery_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"RecoveryCase {recovery_case_id} "
                "does not exist."
            ),
        )

    actions = (
        db.query(RecoveryAction)
        .filter(
            RecoveryAction.recovery_case_id
            == recovery_case_id
        )
        .order_by(
            RecoveryAction.id.asc()
        )
        .all()
    )

    return [
        RecoveryActionResponse(
            **recovery_action_to_dict(action)
        )
        for action in actions
    ]


# ============================================================================
# GET AUDIT LOGS
# ============================================================================


@router.get(
    "/{recovery_case_id}/audit",
    response_model=list[AuditLogResponse],
    status_code=status.HTTP_200_OK,
)
def get_recovery_audit_logs(
    recovery_case_id: int,
    db: Session = Depends(get_db),
):
    """
    Retrieve the complete audit history for a recovery case.
    """

    recovery_case = (
        db.query(RecoveryCase)
        .filter(
            RecoveryCase.id == recovery_case_id,
        )
        .first()
    )

    if recovery_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"RecoveryCase {recovery_case_id} "
                "does not exist."
            ),
        )

    logs = (
        db.query(AuditLog)
        .filter(
            AuditLog.recovery_case_id
            == recovery_case_id
        )
        .order_by(
            AuditLog.id.asc()
        )
        .all()
    )

    return [
        AuditLogResponse(
            id=log.id,
            recovery_case_id=log.recovery_case_id,
            event_type=log.event_type,
            actor_type=log.actor_type,
            actor_id=log.actor_id,
            message=log.message,
            event_data=log.event_data,
            created_at=log.created_at,
        )
        for log in logs
    ]
