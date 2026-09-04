from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from backend.app.models.customer import Customer
from backend.app.models.transaction import Transaction


MINIMUM_INACTIVITY_DAYS = 45
AT_RISK_MULTIPLIER = 1.25


MODEL_FEATURE_COLUMNS = [
    "purchase_count",
    "total_spend",
    "average_order_value",
    "max_order_value",
    "total_quantity",
    "unique_product_count",
    "customer_lifetime_days",
    "days_since_last_purchase",
    "average_days_between_orders",
    "median_days_between_orders",
    "average_order_quantity",
    "orders_last_30_days",
    "orders_last_90_days",
    "cancellation_count",
    "cancellation_value",
    "cancellation_rate",
    "at_risk_threshold_days",
]


def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """Convert a value to float safely."""

    if value is None:
        return default

    try:
        result = float(value)

        if pd.isna(result):
            return default

        return result

    except (TypeError, ValueError):
        return default


def _calculate_threshold(
    median_days_between_orders: float | None,
) -> float:
    """
    Calculate the at-risk inactivity threshold.

    Existing project policy:
        threshold = max(
            median_days_between_orders * 1.25,
            45
        )

    If there is no historical interval, use 45 days.
    """

    if median_days_between_orders is None:
        return float(MINIMUM_INACTIVITY_DAYS)

    if pd.isna(median_days_between_orders):
        return float(MINIMUM_INACTIVITY_DAYS)

    return max(
        float(median_days_between_orders)
        * AT_RISK_MULTIPLIER,
        float(MINIMUM_INACTIVITY_DAYS),
    )


def build_customer_features(
    db: Session,
    customer: Customer,
    reference_date: datetime,
) -> dict[str, float]:
    """
    Build the 17 behavioral features required by the production
    recovery model.

    The feature definitions follow the existing customer feature
    engineering logic, adapted to the PostgreSQL/Razorpay schema.

    Important:
    - Only successful historical payments are purchases.
    - The current failed payment is NOT included as a purchase.
    - One historical Razorpay transaction is treated as one order.
    - Missing behavioral history is represented using NaN where
      appropriate so the trained model's imputer can handle it.
    """

    # ============================================================
    # 1. Load customer's transaction history
    # ============================================================

    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.customer_id == customer.id,
            Transaction.created_at <= reference_date,
        )
        .order_by(Transaction.created_at.asc())
        .all()
    )

    # ============================================================
    # 2. Identify successful historical purchases
    # ============================================================

    purchases = [
        transaction
        for transaction in transactions
        if transaction.status.upper()
        in {
            "CAPTURED",
            "AUTHORIZED",
            "SUCCESS",
            "PAID",
        }
    ]

    # ============================================================
    # 3. Convert Razorpay transactions into order-level data
    # ============================================================

    # The original training dataset has invoice/product/quantity
    # information.
    #
    # Razorpay Transaction currently does not.
    #
    # Therefore:
    #   one successful Razorpay transaction = one order
    #   one order = quantity 1
    #   one order = one product for live approximation

    order_dates: list[datetime] = []
    order_values: list[float] = []
    order_quantities: list[float] = []

    for transaction in purchases:
        order_dates.append(transaction.created_at)

        order_values.append(
            _safe_float(transaction.amount)
        )

        order_quantities.append(1.0)

    # ============================================================
    # 4. Basic purchase features
    # ============================================================

    purchase_count = len(order_values)

    total_spend = sum(order_values)

    average_order_value = (
        total_spend / purchase_count
        if purchase_count > 0
        else 0.0
    )

    max_order_value = (
        max(order_values)
        if order_values
        else 0.0
    )

    total_quantity = sum(order_quantities)

    unique_product_count = purchase_count

    average_order_quantity = (
        total_quantity / purchase_count
        if purchase_count > 0
        else 0.0
    )

    # ============================================================
    # 5. Purchase date features
    # ============================================================

    if order_dates:
        first_purchase_date = min(order_dates)
        last_purchase_date = max(order_dates)

        customer_lifetime_days = max(
            (
                last_purchase_date
                - first_purchase_date
            ).total_seconds()
            / 86400.0,
            0.0,
        )

        days_since_last_purchase = max(
            (
                reference_date
                - last_purchase_date
            ).total_seconds()
            / 86400.0,
            0.0,
        )

    else:
        # No successful historical purchase exists.
        #
        # We must NOT use the current failed payment as purchase
        # history because that would leak the current event into
        # the model features.
        #
        # The trained preprocessing pipeline uses median
        # imputation, so NaN is appropriate for an unavailable
        # behavioral measurement.

        customer_lifetime_days = 0.0
        days_since_last_purchase = float("nan")

    # ============================================================
    # 6. Purchase interval features
    # ============================================================

    sorted_dates = sorted(order_dates)

    intervals: list[float] = []

    for index in range(1, len(sorted_dates)):
        interval_days = (
            sorted_dates[index]
            - sorted_dates[index - 1]
        ).total_seconds() / 86400.0

        intervals.append(interval_days)

    if intervals:
        average_days_between_orders = (
            sum(intervals) / len(intervals)
        )

        median_days_between_orders = float(
            pd.Series(intervals).median()
        )

    else:
        average_days_between_orders = None
        median_days_between_orders = None

    # ============================================================
    # 7. Recent activity
    # ============================================================

    thirty_days_ago = (
        reference_date
        - timedelta(days=30)
    )

    ninety_days_ago = (
        reference_date
        - timedelta(days=90)
    )

    orders_last_30_days = sum(
        1
        for date in order_dates
        if date >= thirty_days_ago
    )

    orders_last_90_days = sum(
        1
        for date in order_dates
        if date >= ninety_days_ago
    )

    # ============================================================
    # 8. Cancellation behavior
    # ============================================================

    cancellations = [
        transaction
        for transaction in transactions
        if transaction.status.upper()
        in {
            "CANCELLED",
            "CANCELED",
        }
    ]

    cancellation_count = len(cancellations)

    cancellation_value = sum(
        _safe_float(transaction.amount)
        for transaction in cancellations
    )

    cancellation_denominator = (
        purchase_count
        + cancellation_count
    )

    cancellation_rate = (
        cancellation_count
        / cancellation_denominator
        if cancellation_denominator > 0
        else 0.0
    )

    # ============================================================
    # 9. At-risk threshold
    # ============================================================

    at_risk_threshold_days = _calculate_threshold(
        median_days_between_orders
    )

    # ============================================================
    # 10. Build exactly the 17 model features
    # ============================================================

    features: dict[str, float] = {
        "purchase_count": float(
            purchase_count
        ),

        "total_spend": float(
            total_spend
        ),

        "average_order_value": float(
            average_order_value
        ),

        "max_order_value": float(
            max_order_value
        ),

        "total_quantity": float(
            total_quantity
        ),

        "unique_product_count": float(
            unique_product_count
        ),

        "customer_lifetime_days": float(
            customer_lifetime_days
        ),

        "days_since_last_purchase": float(
            days_since_last_purchase
        ),

        "average_days_between_orders": (
            float(average_days_between_orders)
            if average_days_between_orders is not None
            else float("nan")
        ),

        "median_days_between_orders": (
            float(median_days_between_orders)
            if median_days_between_orders is not None
            else float("nan")
        ),

        "average_order_quantity": float(
            average_order_quantity
        ),

        "orders_last_30_days": float(
            orders_last_30_days
        ),

        "orders_last_90_days": float(
            orders_last_90_days
        ),

        "cancellation_count": float(
            cancellation_count
        ),

        "cancellation_value": float(
            cancellation_value
        ),

        "cancellation_rate": float(
            cancellation_rate
        ),

        "at_risk_threshold_days": float(
            at_risk_threshold_days
        ),
    }

    # ============================================================
    # 11. Validate model feature set
    # ============================================================

    missing = [
        column
        for column in MODEL_FEATURE_COLUMNS
        if column not in features
    ]

    if missing:
        raise ValueError(
            "Missing model features: "
            + ", ".join(missing)
        )

    if len(features) != len(MODEL_FEATURE_COLUMNS):
        raise ValueError(
            "Unexpected model feature count: "
            f"{len(features)}. "
            f"Expected {len(MODEL_FEATURE_COLUMNS)}."
        )

    # ============================================================
    # 12. Validate numeric values
    # ============================================================

    for column in MODEL_FEATURE_COLUMNS:
        value = features[column]

        # NaN is intentionally allowed because the trained
        # SimpleImputer handles missing behavioral features.
        if pd.isna(value):
            continue

        if not isinstance(value, (int, float)):
            raise ValueError(
                f"Non-numeric model feature: {column}"
            )

    return features