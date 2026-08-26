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

FEATURES_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

CUSTOMER_FEATURES_PATH = (
    FEATURES_DIR
    / "customer_features.parquet"
)


def load_processed_data() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:
    """Load validated processed transaction data."""

    transactions = pd.read_parquet(
        TRANSACTIONS_PATH,
        engine="pyarrow",
    )

    cancellations = pd.read_parquet(
        CANCELLATIONS_PATH,
        engine="pyarrow",
    )

    return transactions, cancellations


def calculate_order_level_data(
    transactions: pd.DataFrame,
) -> pd.DataFrame:
    """
    Aggregate transaction lines into invoice/order-level
    records before calculating customer behavior.
    """

    orders = (
        transactions
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
            unique_products=(
                "stock_code",
                "nunique",
            ),
        )
    )

    return orders


def calculate_customer_features(
    transactions: pd.DataFrame,
    cancellations: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build customer-level behavioral features.
    """

    transactions = transactions.copy()
    cancellations = cancellations.copy()

    # --------------------------------------------------------
    # Reference date
    # --------------------------------------------------------

    reference_date = transactions[
        "invoice_date"
    ].max()

    # --------------------------------------------------------
    # Order-level aggregation
    # --------------------------------------------------------

    orders = calculate_order_level_data(
        transactions
    )

    # --------------------------------------------------------
    # Basic customer features
    # --------------------------------------------------------

    features = (
        orders
        .groupby(
            "customer_id",
            as_index=False,
        )
        .agg(
            purchase_count=(
                "order_value",
                "count",
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
            unique_invoice_count=(
                "invoice",
                "nunique",
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

    # --------------------------------------------------------
    # Customer lifetime
    # --------------------------------------------------------

    features["customer_lifetime_days"] = (
        features["last_purchase_date"]
        - features["first_purchase_date"]
    ).dt.total_seconds() / 86400

    features["days_since_last_purchase"] = (
        reference_date
        - features["last_purchase_date"]
    ).dt.total_seconds() / 86400

    # --------------------------------------------------------
    # Product diversity
    # --------------------------------------------------------

    product_counts = (
        transactions
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

    # --------------------------------------------------------
    # Purchase interval features
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Recent activity
    # --------------------------------------------------------

    thirty_days_ago = (
        reference_date
        - pd.Timedelta(days=30)
    )

    ninety_days_ago = (
        reference_date
        - pd.Timedelta(days=90)
    )

    recent_30 = (
        orders[
            orders["order_date"]
            >= thirty_days_ago
        ]
        .groupby("customer_id")
        .size()
        .rename("orders_last_30_days")
    )

    recent_90 = (
        orders[
            orders["order_date"]
            >= ninety_days_ago
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

    # --------------------------------------------------------
    # Cancellation behavior
    # --------------------------------------------------------

    cancellation_features = (
        cancellations
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

    # --------------------------------------------------------
    # Fill cancellation features
    # --------------------------------------------------------

    features["cancellation_count"] = (
        features["cancellation_count"]
        .fillna(0)
        .astype(int)
    )

    features["cancellation_value"] = (
        features["cancellation_value"]
        .fillna(0.0)
    )

    # --------------------------------------------------------
    # Cancellation rate
    # --------------------------------------------------------

    features["cancellation_rate"] = (
        features["cancellation_count"]
        / (
            features["purchase_count"]
            + features["cancellation_count"]
        )
    )

    # --------------------------------------------------------
    # Recent activity defaults
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Numeric cleanup
    # --------------------------------------------------------

    numeric_columns = [
        "customer_lifetime_days",
        "days_since_last_purchase",
        "average_days_between_orders",
        "median_days_between_orders",
        "average_order_value",
        "max_order_value",
        "average_order_quantity",
        "cancellation_rate",
    ]

    for column in numeric_columns:
        features[column] = (
            features[column]
            .replace(
                [float("inf"), float("-inf")],
                pd.NA,
            )
        )

    # --------------------------------------------------------
    # Final ordering
    # --------------------------------------------------------

    ordered_columns = [
        "customer_id",
        "purchase_count",
        "total_spend",
        "average_order_value",
        "max_order_value",
        "total_quantity",
        "unique_invoice_count",
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
        ordered_columns
    ].sort_values(
        "customer_id"
    ).reset_index(
        drop=True
    )

    return features


def save_features(
    features: pd.DataFrame,
) -> None:

    FEATURES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    features.to_parquet(
        CUSTOMER_FEATURES_PATH,
        index=False,
        engine="pyarrow",
    )


def main() -> None:

    print("=" * 60)
    print("CUSTOMER BEHAVIORAL FEATURE ENGINEERING")
    print("=" * 60)

    print()
    print("1. Loading processed data...")

    transactions, cancellations = (
        load_processed_data()
    )

    print(
        f"   Transactions: "
        f"{len(transactions):,}"
    )

    print(
        f"   Cancellations: "
        f"{len(cancellations):,}"
    )

    print()
    print("2. Building customer features...")

    features = calculate_customer_features(
        transactions,
        cancellations,
    )

    print(
        f"   Customers: "
        f"{len(features):,}"
    )

    print(
        f"   Features: "
        f"{len(features.columns):,}"
    )

    print()
    print("3. Saving features...")

    save_features(features)

    print()
    print(
        f"Saved: "
        f"{CUSTOMER_FEATURES_PATH}"
    )

    print()
    print("Feature columns:")

    for column in features.columns:
        print(f"  - {column}")

    print()
    print("=" * 60)
    print("FEATURE ENGINEERING COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()