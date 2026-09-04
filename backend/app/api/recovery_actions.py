from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.auth import (
    get_db,
    require_management_user,
)
from backend.app.models import RecoveryAction, User
from backend.app.services.recovery.action_executor import (
    RecoveryActionExecutor,
    recovery_action_to_dict,
)


# =========================================================
# ROUTER
# =========================================================

router = APIRouter(
    prefix="/api/v1/recovery-actions",
    tags=["Recovery Actions"],
)


# =========================================================
# SCHEMAS
# =========================================================

class ApprovalRequest(BaseModel):
    approval_reason: str | None = None


# =========================================================
# GET ALL RECOVERY ACTIONS
# =========================================================

@router.get(
    "",
    status_code=status.HTTP_200_OK,
)
def get_all_recovery_actions(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management_user),
) -> list[dict[str, Any]]:
    """
    Return all recovery actions for the management dashboard.
    """

    actions = db.scalars(
        select(RecoveryAction)
        .order_by(RecoveryAction.id.desc())
    ).all()

    return [
        recovery_action_to_dict(action)
        for action in actions
    ]


# =========================================================
# APPROVE RECOVERY ACTION
# =========================================================

@router.post(
    "/{action_id}/approve",
    status_code=status.HTTP_200_OK,
)
def approve_recovery_action(
    action_id: int,
    request: ApprovalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management_user),
) -> dict[str, Any]:
    """
    Approve a recovery action that is waiting for
    human management approval.

    Approval changes:

        PENDING_APPROVAL -> PENDING

    The existing RecoveryActionExecutor is responsible
    for the actual state transition and audit logging.
    """

    executor = RecoveryActionExecutor()

    try:
        action = executor.approve(
            db=db,
            action_id=action_id,
            approver_id=str(current_user.id),
            approval_reason=request.approval_reason,
        )

        db.commit()
        db.refresh(action)

        return recovery_action_to_dict(action)

    except PermissionError as exc:
        db.rollback()

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

    except Exception:
        db.rollback()
        raise


# =========================================================
# EXECUTE RECOVERY ACTION
# =========================================================

@router.post(
    "/{action_id}/execute",
    status_code=status.HTTP_200_OK,
)
def execute_recovery_action(
    action_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_management_user),
) -> dict[str, Any]:
    """
    Execute an approved/ready recovery action.

    The current RecoveryActionExecutor operates in
    simulated mode and does not move real money.

    Expected state transition:

        PENDING -> COMPLETED

    and the associated recovery case becomes:

        OPEN -> RECOVERED
    """

    executor = RecoveryActionExecutor()

    try:
        action = executor.execute(
            db=db,
            action_id=action_id,
        )

        db.commit()
        db.refresh(action)

        return recovery_action_to_dict(action)

    except PermissionError as exc:
        db.rollback()

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

    except Exception:
        db.rollback()
        raise