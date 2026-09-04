from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Header, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.config.settings import RAZORPAY_WEBHOOK_SECRET
from backend.app.db.session import SessionLocal
from backend.app.models.agent_decision import AgentDecision
from backend.app.models.customer import Customer
from backend.app.models.recovery_case import RecoveryCase
from backend.app.models.transaction import Transaction
from backend.app.models.webhook_event import WebhookEvent
from backend.app.services.recovery.live_recovery import LiveRecoveryService


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(
    prefix="/api/v1/webhooks",
    tags=["Webhooks"],
)


# ============================================================================
# CONSTANTS
# ============================================================================

SUPPORTED_EVENTS = {
    "payment.failed",
    "payment.captured",
    "payment.authorized",
}


# ============================================================================
# LIVE RECOVERY SERVICE
# ============================================================================

live_recovery_service = LiveRecoveryService()


# ============================================================================
# SIGNATURE VALIDATION
# ============================================================================

def verify_razorpay_signature(
    raw_body: bytes,
    received_signature: str,
) -> bool:
    """
    Verify the Razorpay webhook signature.

    Razorpay signs the RAW request body using HMAC-SHA256
    with the configured webhook secret.
    """

    if not RAZORPAY_WEBHOOK_SECRET:
        raise RuntimeError(
            "RAZORPAY_WEBHOOK_SECRET is not configured."
        )

    expected_signature = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(
        expected_signature,
        received_signature,
    )


# ============================================================================
# DATABASE
# ============================================================================

def get_db():
    """
    Provide a SQLAlchemy database session.
    """

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ============================================================================
# PAYMENT EXTRACTION
# ============================================================================

def extract_payment_entity(
    payload: dict,
) -> dict:
    """
    Extract payment.entity from a Razorpay webhook payload.
    """

    payment_payload = (
        payload.get("payload", {})
        .get("payment", {})
    )

    if not isinstance(payment_payload, dict):
        raise ValueError(
            "Invalid Razorpay webhook payload: "
            "payment payload missing."
        )

    payment_entity = payment_payload.get("entity")

    if not isinstance(payment_entity, dict):
        raise ValueError(
            "Invalid Razorpay webhook payload: "
            "payment entity missing."
        )

    return payment_entity


# ============================================================================
# CUSTOMER RESOLUTION
# ============================================================================

def resolve_customer_id(
    db: Session,
    payment: dict,
) -> int | None:
    """
    Resolve the internal customer ID from Razorpay payment notes.

    Supported identifiers, in priority order:

        1. customer_access_id
        2. external_customer_id
        3. legacy numeric customer_id

    The internal database customer ID is never required to be
    exposed through the public customer-facing API.
    """

    notes = payment.get("notes")

    if not isinstance(notes, dict):
        return None

    # ------------------------------------------------------------------
    # 1. Customer Access ID
    # ------------------------------------------------------------------

    customer_access_id = notes.get("customer_access_id")

    if customer_access_id:
        normalized_access_id = (
            str(customer_access_id)
            .strip()
            .upper()
        )

        customer = (
            db.query(Customer)
            .filter(
                Customer.customer_access_id
                == normalized_access_id
            )
            .first()
        )

        if customer is not None:
            return customer.id

    # ------------------------------------------------------------------
    # 2. External Customer ID
    # ------------------------------------------------------------------

    external_customer_id = notes.get(
        "external_customer_id"
    )

    if external_customer_id:
        normalized_external_id = (
            str(external_customer_id)
            .strip()
        )

        customer = (
            db.query(Customer)
            .filter(
                Customer.external_customer_id
                == normalized_external_id
            )
            .first()
        )

        if customer is not None:
            return customer.id

    # ------------------------------------------------------------------
    # 3. Legacy / Demo Numeric Customer ID
    # ------------------------------------------------------------------

    raw_customer_id = notes.get("customer_id")

    if raw_customer_id is None:
        return None

    try:
        customer_id = int(raw_customer_id)

    except (TypeError, ValueError):
        return None

    if customer_id <= 0:
        return None

    customer = db.get(
        Customer,
        customer_id,
    )

    if customer is None:
        return None

    return customer.id


# ============================================================================
# TRANSACTION UPSERT
# ============================================================================

def upsert_transaction(
    db: Session,
    *,
    event_type: str,
    payment: dict,
) -> Transaction | None:
    """
    Create or update a transaction from a Razorpay payment event.

    payment.failed:
        creates or updates a FAILED transaction.

    payment.authorized:
        creates or updates an AUTHORIZED transaction.

    payment.captured:
        creates or updates a CAPTURED transaction.

    If the customer cannot be resolved, no transaction is created.
    """

    razorpay_payment_id = payment.get("id")

    if not razorpay_payment_id:
        raise ValueError(
            "Razorpay payment ID is missing."
        )

    # ------------------------------------------------------------------
    # Resolve customer
    # ------------------------------------------------------------------

    customer_id = resolve_customer_id(
        db,
        payment,
    )

    if customer_id is None:
        return None

    # ------------------------------------------------------------------
    # Amount
    # ------------------------------------------------------------------

    amount_raw = payment.get("amount")

    if amount_raw is None:
        raise ValueError(
            "Payment amount is missing."
        )

    try:
        amount = (
            Decimal(str(amount_raw))
            / Decimal("100")
        )
    except Exception as exc:
        raise ValueError(
            "Invalid Razorpay payment amount."
        ) from exc

    if amount < 0:
        raise ValueError(
            "Payment amount cannot be negative."
        )

    # ------------------------------------------------------------------
    # Currency
    # ------------------------------------------------------------------

    currency = str(
        payment.get("currency")
        or "INR"
    ).upper()

    # ------------------------------------------------------------------
    # Transaction status
    # ------------------------------------------------------------------

    status_map = {
        "payment.failed": "FAILED",
        "payment.authorized": "AUTHORIZED",
        "payment.captured": "CAPTURED",
    }

    transaction_status = status_map.get(
        event_type,
        str(
            payment.get("status")
            or "UNKNOWN"
        ).upper(),
    )

    # ------------------------------------------------------------------
    # Failure reason
    # ------------------------------------------------------------------

    failure_reason = None

    if event_type == "payment.failed":
        failure_reason = (
            payment.get("error_description")
            or payment.get("error_reason")
            or payment.get("error_code")
            or "Payment failed"
        )

    # ------------------------------------------------------------------
    # Additional Razorpay information
    # ------------------------------------------------------------------

    payment_method = payment.get("method")

    razorpay_order_id = payment.get(
        "order_id"
    )

    # ------------------------------------------------------------------
    # Find existing transaction
    # ------------------------------------------------------------------

    transaction = (
        db.query(Transaction)
        .filter(
            Transaction.razorpay_payment_id
            == razorpay_payment_id
        )
        .first()
    )

    # ------------------------------------------------------------------
    # Existing transaction
    # ------------------------------------------------------------------

    if transaction is not None:

        transaction.customer_id = customer_id
        transaction.amount = amount
        transaction.currency = currency
        transaction.status = transaction_status
        transaction.updated_at = datetime.utcnow()

        if failure_reason:
            transaction.failure_reason = (
                failure_reason
            )

        if payment_method:
            transaction.payment_method = (
                payment_method
            )

        if razorpay_order_id:
            transaction.razorpay_order_id = (
                razorpay_order_id
            )

        db.flush()

        return transaction

    # ------------------------------------------------------------------
    # New transaction
    # ------------------------------------------------------------------

    transaction = Transaction(
        external_transaction_id=(
            razorpay_payment_id
        ),
        customer_id=customer_id,
        amount=amount,
        currency=currency,
        status=transaction_status,
        failure_reason=failure_reason,
        payment_method=payment_method,
        razorpay_payment_id=(
            razorpay_payment_id
        ),
        razorpay_order_id=(
            razorpay_order_id
        ),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(transaction)

    db.flush()

    return transaction


# ============================================================================
# WEBHOOK ENDPOINT
# ============================================================================

@router.post(
    "/razorpay",
    status_code=status.HTTP_200_OK,
)
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(
        default=None,
        alias="X-Razorpay-Signature",
    ),
    x_razorpay_event_id: str | None = Header(
        default=None,
        alias="X-Razorpay-Event-Id",
    ),
):
    """
    Receive Razorpay webhook events.

    Security sequence:

        1. Read raw request body.
        2. Validate Razorpay HMAC signature.
        3. Require Razorpay event ID.
        4. Parse JSON.
        5. Deduplicate event.
        6. Persist webhook event.
        7. Process supported payment events.
        8. Run live recovery for payment.failed.
        9. Commit processing result.

    Razorpay may retry the same event, so this endpoint
    is designed to be idempotent.
    """

    # ==================================================================
    # 1. READ RAW REQUEST BODY
    # ==================================================================

    raw_body = await request.body()

    if not raw_body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook body is empty.",
        )

    # ==================================================================
    # 2. VALIDATE SIGNATURE
    # ==================================================================

    if not x_razorpay_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Razorpay webhook signature.",
        )

    try:
        signature_valid = (
            verify_razorpay_signature(
                raw_body=raw_body,
                received_signature=(
                    x_razorpay_signature
                ),
            )
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=str(exc),
        ) from exc

    if not signature_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Razorpay webhook signature.",
        )

    # ==================================================================
    # 3. REQUIRE EVENT ID
    # ==================================================================

    if not x_razorpay_event_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Razorpay event ID.",
        )

    # ==================================================================
    # 4. PARSE JSON AFTER SIGNATURE VALIDATION
    # ==================================================================

    try:
        payload = json.loads(
            raw_body.decode("utf-8")
        )

    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON webhook payload.",
        ) from exc

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Webhook payload must be "
                "a JSON object."
            ),
        )

    event_type = payload.get("event")

    if not isinstance(event_type, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook event type is missing.",
        )

    # ==================================================================
    # 5. DATABASE SESSION
    # ==================================================================

    db = SessionLocal()

    try:

        # ==============================================================
        # 6. IDEMPOTENCY CHECK
        # ==============================================================

        existing_event = (
            db.query(WebhookEvent)
            .filter(
                WebhookEvent.event_id
                == x_razorpay_event_id
            )
            .first()
        )

        if existing_event is not None:
            return {
                "status": "already_processed",
                "event_id": x_razorpay_event_id,
            }

        # ==============================================================
        # 7. STORE INCOMING EVENT
        # ==============================================================

        webhook_event = WebhookEvent(
            event_id=x_razorpay_event_id,
            event_type=event_type,
            signature_verified=True,
            processing_status="RECEIVED",
            payload=payload,
            received_at=datetime.utcnow(),
        )

        db.add(webhook_event)

        db.flush()

        # ==============================================================
        # 8. IGNORE UNSUPPORTED EVENTS SAFELY
        # ==============================================================

        if event_type not in SUPPORTED_EVENTS:

            webhook_event.processing_status = (
                "IGNORED"
            )

            webhook_event.processed_at = (
                datetime.utcnow()
            )

            db.commit()

            return {
                "status": "ignored",
                "event_id": (
                    x_razorpay_event_id
                ),
                "event": event_type,
            }

        # ==============================================================
        # 9. EXTRACT PAYMENT
        # ==============================================================

        try:
            payment = extract_payment_entity(
                payload
            )

        except ValueError as exc:

            webhook_event.processing_status = (
                "FAILED"
            )

            webhook_event.error_message = str(
                exc
            )

            webhook_event.processed_at = (
                datetime.utcnow()
            )

            db.commit()

            raise HTTPException(
                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),
                detail=str(exc),
            ) from exc

        # ==============================================================
        # 10. PROCESS TRANSACTION
        # ==============================================================

        try:
            transaction = upsert_transaction(
                db=db,
                event_type=event_type,
                payment=payment,
            )

        except ValueError as exc:

            webhook_event.processing_status = (
                "FAILED"
            )

            webhook_event.error_message = str(
                exc
            )

            webhook_event.processed_at = (
                datetime.utcnow()
            )

            db.commit()

            raise HTTPException(
                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),
                detail=str(exc),
            ) from exc

        # ==============================================================
        # 11. CUSTOMER COULD NOT BE RESOLVED
        # ==============================================================

        if transaction is None:

            webhook_event.processing_status = (
                "UNRESOLVED_CUSTOMER"
            )

            webhook_event.error_message = (
                "Could not resolve customer from "
                "payment notes. Supported identifiers: "
                "customer_access_id, "
                "external_customer_id, customer_id."
            )

            webhook_event.processed_at = (
                datetime.utcnow()
            )

            db.commit()

            return {
                "status": "received",
                "event_id": (
                    x_razorpay_event_id
                ),
                "event": event_type,
                "transaction_created": False,
                "reason": "customer_not_resolved",
            }

        # ==============================================================
        # 12. LIVE AI RECOVERY PIPELINE
        # ==============================================================

        recovery_case = None
        agent_decision = None

        if event_type == "payment.failed":

            try:

                recovery_case = (
                    live_recovery_service
                    .process_failed_transaction(
                        db,
                        transaction=transaction,
                    )
                )

                # ------------------------------------------------------
                # Retrieve the decision created by the service
                # ------------------------------------------------------

                agent_decision = (
                    db.query(AgentDecision)
                    .filter(
                        AgentDecision.recovery_case_id
                        == recovery_case.id
                    )
                    .order_by(
                        AgentDecision.id.desc()
                    )
                    .first()
                )

            except Exception as exc:

                webhook_event.processing_status = (
                    "FAILED"
                )

                webhook_event.error_message = (
                    "Live recovery processing "
                    f"failed: {exc}"
                )

                webhook_event.processed_at = (
                    datetime.utcnow()
                )

                db.commit()

                raise HTTPException(
                    status_code=(
                        status.HTTP_500_INTERNAL_SERVER_ERROR
                    ),
                    detail=(
                        "Live recovery "
                        "processing failed."
                    ),
                ) from exc

        # ==============================================================
        # 13. PAYMENT AUTHORIZED / CAPTURED
        # ==============================================================

        # These events update the transaction state.
        #
        # Recovery outcome is intentionally not automatically marked
        # here because a captured payment does not necessarily prove
        # that a particular recovery action caused the payment.
        #
        # This prevents unrelated captured payments from being
        # incorrectly recorded as recovered revenue.

        # ==============================================================
        # 14. SUCCESS
        # ==============================================================

        webhook_event.processing_status = (
            "PROCESSED"
        )

        webhook_event.processed_at = (
            datetime.utcnow()
        )

        db.commit()

        response = {
            "status": "processed",
            "event_id": x_razorpay_event_id,
            "event": event_type,
            "transaction_id": transaction.id,
            "transaction_status": transaction.status,
        }

        if recovery_case is not None:
            response[
                "recovery_case_id"
            ] = recovery_case.id

        if agent_decision is not None:

            response[
                "agent_decision_id"
            ] = agent_decision.id

            response[
                "decision"
            ] = agent_decision.decision

            response[
                "requires_human_approval"
            ] = (
                agent_decision
                .requires_human_approval
            )

        return response

    # ==================================================================
    # CONCURRENT / DUPLICATE EVENT
    # ==================================================================

    except HTTPException:
        raise

    except IntegrityError:

        db.rollback()

        existing_event = (
            db.query(WebhookEvent)
            .filter(
                WebhookEvent.event_id
                == x_razorpay_event_id
            )
            .first()
        )

        if existing_event is not None:
            return {
                "status": "already_processed",
                "event_id": x_razorpay_event_id,
            }

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Webhook persistence failed.",
        )

    # ==================================================================
    # UNEXPECTED ERROR
    # ==================================================================

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Webhook processing failed.",
        )

    finally:

        db.close()