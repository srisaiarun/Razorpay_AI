from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.app.models.recovery_action import RecoveryAction
from backend.app.db.session import SessionLocal
from backend.app.services.recovery.action_executor import (
    RecoveryActionExecutor,
    recovery_action_to_dict,
)


router = APIRouter(
    prefix="/api/v1/recovery-actions",
    tags=["Recovery Actions"],
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


class RecoveryActionApprovalRequest(BaseModel):
    """
    Request body used by a human reviewer to approve
    a recovery action.
    """

    approver_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    approval_reason: str | None = Field(
        default=None,
        max_length=500,
    )


class RecoveryActionResponse(BaseModel):
    """
    API representation of a recovery action.
    """

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

# ----------------------------------------------------------------------
# LIST ALL RECOVERY ACTIONS
# ----------------------------------------------------------------------

@router.get(
    "",
    response_model=list[RecoveryActionResponse],
    status_code=status.HTTP_200_OK,
)
def get_all_recovery_actions(
    db: Session = Depends(get_db),
):
    """
    Return all persisted recovery actions for the admin UI.

    Actions are ordered newest first.
    """

    actions = (
        db.query(RecoveryAction)
        .order_by(RecoveryAction.created_at.desc())
        .all()
    )

    return [
        recovery_action_to_dict(action)
        for action in actions
    ]

# ----------------------------------------------------------------------
# APPROVE
# ----------------------------------------------------------------------

@router.post(
    "/{action_id}/approve",
    response_model=RecoveryActionResponse,
    status_code=status.HTTP_200_OK,
)
def approve_recovery_action(
    action_id: int,
    request: RecoveryActionApprovalRequest,
    db: Session = Depends(get_db),
):
    """
    Approve a recovery action requiring human approval.

    This endpoint does NOT execute the action.

    State transition:

        PENDING_APPROVAL
            ->
        PENDING

    The actual execution must happen through the
    /execute endpoint afterward.
    """

    executor = RecoveryActionExecutor()

    try:
        action = executor.approve(
            db,
            action_id=action_id,
            approver_id=request.approver_id,
            approval_reason=request.approval_reason,
        )

        db.commit()
        db.refresh(action)

        return recovery_action_to_dict(action)

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
            detail="Recovery action approval failed.",
        ) from exc


# ----------------------------------------------------------------------
# EXECUTE
# ----------------------------------------------------------------------

@router.post(
    "/{action_id}/execute",
    response_model=RecoveryActionResponse,
    status_code=status.HTTP_200_OK,
)
def execute_recovery_action(
    action_id: int,
    db: Session = Depends(get_db),
):
    """
    Execute a recovery action in simulated mode.

    PENDING actions can execute.

    PENDING_APPROVAL actions are blocked until
    explicitly approved by a human reviewer.
    """

    executor = RecoveryActionExecutor()

    try:
        action = executor.execute(
            db,
            action_id=action_id,
        )

        db.commit()
        db.refresh(action)

        return recovery_action_to_dict(action)

    except PermissionError as exc:
        # The executor intentionally creates an audit record
        # documenting the blocked execution attempt.
        #
        # Commit that audit record before returning 403.
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

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
            detail="Recovery action execution failed.",
        ) from exc