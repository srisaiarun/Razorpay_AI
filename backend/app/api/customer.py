from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.api.auth import require_customer_user
from backend.app.db.session import SessionLocal
from backend.app.models.customer import Customer
from backend.app.models.recovery_case import RecoveryCase
from backend.app.models.transaction import Transaction
from backend.app.models.user import User


router = APIRouter(
    prefix="/api/v1/customer",
    tags=["Customer"],
    dependencies=[Depends(require_customer_user)],
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================


class CustomerProfileResponse(BaseModel):
    id: int
    external_customer_id: str
    name: str
    email: str
    lifetime_value: float
    successful_payments: int
    failed_payments: int
    opted_out: bool


class CustomerSummaryResponse(BaseModel):
    customer_id: int
    lifetime_value: float
    successful_payments: int
    failed_payments: int
    total_transactions: int
    open_recovery_cases: int
    recovered_cases: int
    amount_at_risk: float
    recovery_rate: float


class CustomerTransactionResponse(BaseModel):
    id: int
    external_transaction_id: str
    amount: float
    currency: str
    status: str
    failure_reason: str | None
    payment_method: str | None
    razorpay_payment_id: str | None
    razorpay_order_id: str | None
    created_at: str


class CustomerRecoveryCaseResponse(BaseModel):
    id: int
    transaction_id: int
    amount_at_risk: float
    failure_class: str
    risk_score: float
    recovery_probability: float | None
    status: str
    attempt_count: int
    next_action_at: str | None
    created_at: str
    resolved_at: str | None


# ============================================================================
# CUSTOMER PROFILE
# ============================================================================


@router.get(
    "/me",
    response_model=CustomerProfileResponse,
    status_code=status.HTTP_200_OK,
)
def get_customer_profile(
    current_user: User = Depends(require_customer_user),
    db: Session = Depends(get_db),
):
    """
    Return the authenticated customer's profile.

    The customer ID is taken from the authenticated JWT-linked
    user record. It is never accepted from the client.
    """

    if current_user.customer_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer account is not linked to a customer profile.",
        )

    customer = (
        db.query(Customer)
        .filter(
            Customer.id == current_user.customer_id,
        )
        .first()
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer profile not found.",
        )

    return CustomerProfileResponse(
        id=customer.id,
        external_customer_id=customer.external_customer_id,
        name=customer.name,
        email=customer.email,
        lifetime_value=float(customer.lifetime_value),
        successful_payments=customer.successful_payments,
        failed_payments=customer.failed_payments,
        opted_out=customer.opted_out,
    )


# ============================================================================
# CUSTOMER SUMMARY
# ============================================================================


@router.get(
    "/summary",
    response_model=CustomerSummaryResponse,
    status_code=status.HTTP_200_OK,
)
def get_customer_summary(
    current_user: User = Depends(require_customer_user),
    db: Session = Depends(get_db),
):
    """
    Return payment and recovery metrics for the authenticated customer.
    """

    if current_user.customer_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer account is not linked to a customer profile.",
        )

    customer = (
        db.query(Customer)
        .filter(
            Customer.id == current_user.customer_id,
        )
        .first()
    )

    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer profile not found.",
        )

    total_transactions = (
        db.query(Transaction)
        .filter(
            Transaction.customer_id == customer.id,
        )
        .count()
    )

    open_recovery_cases = (
        db.query(RecoveryCase)
        .filter(
            RecoveryCase.customer_id == customer.id,
            RecoveryCase.status == "OPEN",
        )
        .count()
    )

    recovered_cases = (
        db.query(RecoveryCase)
        .filter(
            RecoveryCase.customer_id == customer.id,
            RecoveryCase.status == "RECOVERED",
        )
        .count()
    )

    amount_at_risk_result = (
        db.query(RecoveryCase.amount_at_risk)
        .filter(
            RecoveryCase.customer_id == customer.id,
            RecoveryCase.status == "OPEN",
        )
        .all()
    )

    amount_at_risk = sum(
        Decimal(str(row[0]))
        for row in amount_at_risk_result
        if row[0] is not None
    )

    total_failed = customer.failed_payments
    recovered_count = recovered_cases

    if total_failed > 0:
        recovery_rate = recovered_count / total_failed
    else:
        recovery_rate = 0.0

    return CustomerSummaryResponse(
        customer_id=customer.id,
        lifetime_value=float(customer.lifetime_value),
        successful_payments=customer.successful_payments,
        failed_payments=customer.failed_payments,
        total_transactions=total_transactions,
        open_recovery_cases=open_recovery_cases,
        recovered_cases=recovered_cases,
        amount_at_risk=float(amount_at_risk),
        recovery_rate=recovery_rate,
    )


# ============================================================================
# CUSTOMER TRANSACTIONS
# ============================================================================


@router.get(
    "/transactions",
    response_model=list[CustomerTransactionResponse],
    status_code=status.HTTP_200_OK,
)
def get_customer_transactions(
    current_user: User = Depends(require_customer_user),
    db: Session = Depends(get_db),
):
    """
    Return transactions belonging only to the authenticated customer.
    """

    if current_user.customer_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer account is not linked to a customer profile.",
        )

    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.customer_id == current_user.customer_id,
        )
        .order_by(
            Transaction.created_at.desc(),
        )
        .all()
    )

    return [
        CustomerTransactionResponse(
            id=transaction.id,
            external_transaction_id=transaction.external_transaction_id,
            amount=float(transaction.amount),
            currency=transaction.currency,
            status=transaction.status,
            failure_reason=transaction.failure_reason,
            payment_method=transaction.payment_method,
            razorpay_payment_id=transaction.razorpay_payment_id,
            razorpay_order_id=transaction.razorpay_order_id,
            created_at=transaction.created_at.isoformat(),
        )
        for transaction in transactions
    ]


# ============================================================================
# CUSTOMER RECOVERY CASES
# ============================================================================


@router.get(
    "/recovery-cases",
    response_model=list[CustomerRecoveryCaseResponse],
    status_code=status.HTTP_200_OK,
)
def get_customer_recovery_cases(
    current_user: User = Depends(require_customer_user),
    db: Session = Depends(get_db),
):
    """
    Return recovery cases belonging only to the authenticated customer.
    """

    if current_user.customer_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customer account is not linked to a customer profile.",
        )

    recovery_cases = (
        db.query(RecoveryCase)
        .filter(
            RecoveryCase.customer_id == current_user.customer_id,
        )
        .order_by(
            RecoveryCase.created_at.desc(),
        )
        .all()
    )

    return [
        CustomerRecoveryCaseResponse(
            id=recovery_case.id,
            transaction_id=recovery_case.transaction_id,
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
            next_action_at=(
                recovery_case.next_action_at.isoformat()
                if recovery_case.next_action_at is not None
                else None
            ),
            created_at=recovery_case.created_at.isoformat(),
            resolved_at=(
                recovery_case.resolved_at.isoformat()
                if recovery_case.resolved_at is not None
                else None
            ),
        )
        for recovery_case in recovery_cases
    ]