from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

TRANSACTIONS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "transactions.parquet"
)

CANCELLATIONS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "cancellations.parquet"
)


def load_processed_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the cleaned transaction and cancellation datasets."""

    transactions = pd.read_parquet(
        TRANSACTIONS_PATH,
        engine="pyarrow",
    )

    cancellations = pd.read_parquet(
        CANCELLATIONS_PATH,
        engine="pyarrow",
    )

    return transactions, cancellations


def calculate_point_in_time_features(
    transactions: pd.DataFrame,
    cancellations: pd.DataFrame,
    snapshot_date: pd.Timestamp,
) -> pd.DataFrame:
    """
    Calculate customer features using only information
    available on or before snapshot_date.

    This function is the core anti-data-leakage boundary
    for our ML pipeline.
    """

    snapshot_date = pd.Timestamp(snapshot_date)

    # ========================================================
    # 1. Restrict historical information
    # ========================================================

    historical_transactions = transactions[
        transactions["invoice_date"] <= snapshot_date
    ].copy()

    historical_cancellations = cancellations[
        cancellations["invoice_date"] <= snapshot_date
    ].copy()

    if historical_transactions.empty:
        return pd.DataFrame()

    # ========================================================
    # 2. Order-level aggregation
    # ========================================================

    orders = (
        historical_transactions
        .groupby(
            [
                "customer_id",
                "invoice",
            ],
            as_index=False,
        )
        .agg(
            order_date=(
                "invoice_date",
                "min",
            ),
            order_value=(
                "transaction_amount",
                "sum",
            ),
            order_quantity=(
                "quantity",
                "sum",
            ),
        )
    )

    # ========================================================
    # 3. Basic customer features
    # ========================================================

    features = (
        orders
        .groupby(
            "customer_id",
            as_index=False,
        )
        .agg(
            purchase_count=(
                "invoice",
                "nunique",
            ),
            total_spend=(
                "order_value",
                "sum",
            ),
            average_order_value=(
                "order_value",
                "mean",
            ),
            max_order_value=(
                "order_value",
                "max",
            ),
            total_quantity=(
                "order_quantity",
                "sum",
            ),
            first_purchase_date=(
                "order_date",
                "min",
            ),
            last_purchase_date=(
                "order_date",
                "max",
            ),
            average_order_quantity=(
                "order_quantity",
                "mean",
            ),
        )
    )

    # ========================================================
    # 4. Recency
    # ========================================================

    features["days_since_last_purchase"] = (
        snapshot_date
        - features["last_purchase_date"]
    ).dt.total_seconds() / 86400

    features["customer_lifetime_days"] = (
        features["last_purchase_date"]
        - features["first_purchase_date"]
    ).dt.total_seconds() / 86400

    # ========================================================
    # 5. Product diversity
    # ========================================================

    product_counts = (
        historical_transactions
        .groupby("customer_id")["stock_code"]
        .nunique()
        .rename("unique_product_count")
        .reset_index()
    )

    features = features.merge(
        product_counts,
        on="customer_id",
        how="left",
    )

    # ========================================================
    # 6. Purchase intervals
    # ========================================================

    sorted_orders = orders.sort_values(
        [
            "customer_id",
            "order_date",
        ]
    ).copy()

    sorted_orders["previous_order_date"] = (
        sorted_orders
        .groupby("customer_id")["order_date"]
        .shift(1)
    )

    sorted_orders["days_since_previous_order"] = (
        sorted_orders["order_date"]
        - sorted_orders["previous_order_date"]
    ).dt.total_seconds() / 86400

    interval_features = (
        sorted_orders
        .groupby("customer_id")[
            "days_since_previous_order"
        ]
        .agg(
            average_days_between_orders="mean",
            median_days_between_orders="median",
        )
        .reset_index()
    )

    features = features.merge(
        interval_features,
        on="customer_id",
        how="left",
    )

    # ========================================================
    # 7. Recent activity
    # ========================================================

    thirty_days_ago = (
        snapshot_date
        - pd.Timedelta(days=30)
    )

    ninety_days_ago = (
        snapshot_date
        - pd.Timedelta(days=90)
    )

    recent_30 = (
        orders[
            orders["order_date"] > thirty_days_ago
        ]
        .groupby("customer_id")
        .size()
        .rename("orders_last_30_days")
    )

    recent_90 = (
        orders[
            orders["order_date"] > ninety_days_ago
        ]
        .groupby("customer_id")
        .size()
        .rename("orders_last_90_days")
    )

    features = features.merge(
        recent_30,
        on="customer_id",
        how="left",
    )

    features = features.merge(
        recent_90,
        on="customer_id",
        how="left",
    )

    # ========================================================
    # 8. Cancellation behavior
    # ========================================================

    if not historical_cancellations.empty:

        cancellation_features = (
            historical_cancellations
            .groupby("customer_id")
            .agg(
                cancellation_count=(
                    "invoice",
                    "count",
                ),
                cancellation_value=(
                    "transaction_amount",
                    "sum",
                ),
            )
            .reset_index()
        )

        features = features.merge(
            cancellation_features,
            on="customer_id",
            how="left",
        )

    # ========================================================
    # 9. Default missing values
    # ========================================================

    features["cancellation_count"] = (
        features["cancellation_count"]
        .fillna(0)
        .astype(int)
    )

    features["cancellation_value"] = (
        features["cancellation_value"]
        .fillna(0.0)
    )

    features["orders_last_30_days"] = (
        features["orders_last_30_days"]
        .fillna(0)
        .astype(int)
    )

    features["orders_last_90_days"] = (
        features["orders_last_90_days"]
        .fillna(0)
        .astype(int)
    )

    # ========================================================
    # 10. Cancellation ratio
    # ========================================================

    features["cancellation_rate"] = (
        features["cancellation_count"]
        / (
            features["purchase_count"]
            + features["cancellation_count"]
        )
    )

    # ========================================================
    # 11. Clean numeric values
    # ========================================================

    numeric_columns = [
        "days_since_last_purchase",
        "customer_lifetime_days",
        "average_days_between_orders",
        "median_days_between_orders",
        "average_order_value",
        "max_order_value",
        "average_order_quantity",
        "cancellation_rate",
    ]

    for column in numeric_columns:

        if column in features.columns:

            features[column] = (
                features[column]
                .replace(
                    [float("inf"), float("-inf")],
                    pd.NA,
                )
            )

    # ========================================================
    # 12. Snapshot metadata
    # ========================================================

    features["snapshot_date"] = snapshot_date

    # ========================================================
    # 13. Final column order
    # ========================================================

    ordered_columns = [
        "customer_id",
        "snapshot_date",
        "purchase_count",
        "total_spend",
        "average_order_value",
        "max_order_value",
        "total_quantity",
        "unique_product_count",
        "first_purchase_date",
        "last_purchase_date",
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
    ]

    features = features[
        [
            column
            for column in ordered_columns
            if column in features.columns
        ]
    ]

    features = features.sort_values(
        "customer_id"
    ).reset_index(
        drop=True
    )

    return features


def main() -> None:
    """
    Small smoke test for the point-in-time feature calculator.
    """

    print("=" * 60)
    print("POINT-IN-TIME FEATURE CALCULATOR TEST")
    print("=" * 60)

    print()
    print("Loading processed data...")

    transactions, cancellations = (
        load_processed_data()
    )

    print(
        f"Transactions: {len(transactions):,}"
    )

    print(
        f"Cancellations: {len(cancellations):,}"
    )

    # --------------------------------------------------------
    # Pick a date safely inside the dataset
    # --------------------------------------------------------

    min_date = transactions[
        "invoice_date"
    ].min()

    max_date = transactions[
        "invoice_date"
    ].max()

    snapshot_date = (
        min_date
        + (
            max_date - min_date
        ) * 0.60
    )

    snapshot_date = pd.Timestamp(
        snapshot_date
    )

    print()
    print(
        f"Snapshot date: "
        f"{snapshot_date}"
    )

    # --------------------------------------------------------
    # Calculate
    # --------------------------------------------------------

    features = calculate_point_in_time_features(
        transactions=transactions,
        cancellations=cancellations,
        snapshot_date=snapshot_date,
    )

    print()
    print(
        f"Customers at snapshot: "
        f"{len(features):,}"
    )

    print(
        f"Feature columns: "
        f"{len(features.columns):,}"
    )

    # --------------------------------------------------------
    # Leakage checks
    # --------------------------------------------------------

    assert (
        features["last_purchase_date"]
        <= snapshot_date
    ).all()

    assert (
        features["first_purchase_date"]
        <= snapshot_date
    ).all()

    assert (
        features["snapshot_date"]
        == snapshot_date
    ).all()

    print()
    print("[PASS] No customer feature uses future purchases")
    print("[PASS] First purchase dates are before snapshot")
    print("[PASS] Last purchase dates are before snapshot")
    print("[PASS] Snapshot dates are consistent")

    print()
    print("Sample features:")

    print(
        features.head(5).to_string(
            index=False
        )
    )

    print()
    print("=" * 60)
    print("POINT-IN-TIME TEST PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()