from __future__ import annotations

from pathlib import Path

import pandas as pd

from backend.app.services.point_in_time_features import (
    calculate_point_in_time_features,
    load_processed_data,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

TEMPORAL_DATASET_PATH = (
    OUTPUT_DIR
    / "temporal_training_dataset.parquet"
)


# ============================================================
# Configuration
# ============================================================

SNAPSHOT_FREQUENCY = "MS"

FUTURE_WINDOW_DAYS = 90

MINIMUM_INACTIVITY_DAYS = 45

AT_RISK_MULTIPLIER = 1.25

MINIMUM_HISTORY_DAYS = 30


# ============================================================
# Snapshot generation
# ============================================================

def generate_snapshot_dates(
    transactions: pd.DataFrame,
) -> list[pd.Timestamp]:
    """
    Generate monthly snapshot dates that have enough
    historical data and enough future observation time.
    """

    minimum_date = (
        transactions["invoice_date"].min()
        .normalize()
        + pd.Timedelta(
            days=MINIMUM_HISTORY_DAYS
        )
    )

    maximum_date = (
        transactions["invoice_date"].max()
        .normalize()
        - pd.Timedelta(
            days=FUTURE_WINDOW_DAYS
        )
    )

    if minimum_date >= maximum_date:
        raise ValueError(
            "Dataset does not contain enough temporal "
            "coverage for the requested history and "
            "future window."
        )

    dates = pd.date_range(
        start=minimum_date,
        end=maximum_date,
        freq=SNAPSHOT_FREQUENCY,
    )

    return [
        pd.Timestamp(date)
        for date in dates
    ]


# ============================================================
# Future outcomes
# ============================================================

def calculate_future_outcomes(
    transactions: pd.DataFrame,
    snapshot_features: pd.DataFrame,
    snapshot_date: pd.Timestamp,
) -> pd.DataFrame:
    """
    Calculate customer behavior during the future
    observation window.

    IMPORTANT:
    These values are intentionally calculated AFTER
    the snapshot and are used only as labels/outcomes,
    never as input features.
    """

    future_start = (
        snapshot_date
        + pd.Timedelta(
            seconds=1
        )
    )

    future_end = (
        snapshot_date
        + pd.Timedelta(
            days=FUTURE_WINDOW_DAYS
        )
    )

    future_transactions = transactions[
        (transactions["invoice_date"] > future_start)
        & (transactions["invoice_date"] <= future_end)
    ].copy()

    if future_transactions.empty:

        outcomes = snapshot_features[
            ["customer_id"]
        ].copy()

        outcomes["future_purchase_count"] = 0
        outcomes["future_spend"] = 0.0
        outcomes["recovered"] = 0

        return outcomes

    future_orders = (
        future_transactions
        .groupby(
            [
                "customer_id",
                "invoice",
            ],
            as_index=False,
        )
        .agg(
            order_value=(
                "transaction_amount",
                "sum",
            )
        )
    )

    outcomes = (
        future_orders
        .groupby(
            "customer_id",
            as_index=False,
        )
        .agg(
            future_purchase_count=(
                "invoice",
                "nunique",
            ),
            future_spend=(
                "order_value",
                "sum",
            ),
        )
    )

    outcomes["recovered"] = (
        outcomes["future_purchase_count"]
        > 0
    ).astype(int)

    return outcomes


# ============================================================
# At-risk classification
# ============================================================

def identify_at_risk_customers(
    features: pd.DataFrame,
) -> pd.DataFrame:
    """
    Identify customers whose inactivity is meaningfully
    beyond their observed purchasing cadence.

    This is an eligibility rule, not the ML target.
    """

    result = features.copy()

    expected_interval = (
        result["median_days_between_orders"]
    )

    # For customers with multiple orders, use their
    # historical median interval.
    cadence_threshold = (
        expected_interval
        * AT_RISK_MULTIPLIER
    )

    # For customers without a historical interval,
    # use a conservative fixed inactivity threshold.
    cadence_threshold = cadence_threshold.fillna(
        MINIMUM_INACTIVITY_DAYS
    )

    cadence_threshold = cadence_threshold.clip(
        lower=MINIMUM_INACTIVITY_DAYS
    )

    result["at_risk_threshold_days"] = (
        cadence_threshold
    )

    result["at_risk"] = (
        result["days_since_last_purchase"]
        >= result["at_risk_threshold_days"]
    ).astype(int)

    return result


# ============================================================
# Build temporal dataset
# ============================================================

def build_temporal_dataset(
    transactions: pd.DataFrame,
    cancellations: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the complete point-in-time supervised-learning
    dataset.
    """

    snapshot_dates = generate_snapshot_dates(
        transactions
    )

    print()
    print(
        f"Snapshot dates: "
        f"{len(snapshot_dates)}"
    )

    all_snapshots: list[pd.DataFrame] = []

    for index, snapshot_date in enumerate(
        snapshot_dates,
        start=1,
    ):

        print(
            f"  [{index:02d}/{len(snapshot_dates):02d}] "
            f"{snapshot_date.date()}",
            flush=True,
        )

        # ----------------------------------------------------
        # Historical features
        # ----------------------------------------------------

        features = (
            calculate_point_in_time_features(
                transactions=transactions,
                cancellations=cancellations,
                snapshot_date=snapshot_date,
            )
        )

        if features.empty:
            continue

        # ----------------------------------------------------
        # At-risk eligibility
        # ----------------------------------------------------

        features = identify_at_risk_customers(
            features
        )

        # ----------------------------------------------------
        # Future outcome
        # ----------------------------------------------------

        outcomes = calculate_future_outcomes(
            transactions=transactions,
            snapshot_features=features,
            snapshot_date=snapshot_date,
        )

        # ----------------------------------------------------
        # Merge outcome onto snapshot
        # ----------------------------------------------------

        snapshot = features.merge(
            outcomes,
            on="customer_id",
            how="left",
        )

        snapshot["future_purchase_count"] = (
            snapshot[
                "future_purchase_count"
            ]
            .fillna(0)
            .astype(int)
        )

        snapshot["future_spend"] = (
            snapshot["future_spend"]
            .fillna(0.0)
        )

        snapshot["recovered"] = (
            snapshot["recovered"]
            .fillna(0)
            .astype(int)
        )

        # ----------------------------------------------------
        # Only eligible at-risk customers become training
        # examples.
        # ----------------------------------------------------

        snapshot = snapshot[
            snapshot["at_risk"] == 1
        ].copy()

        if not snapshot.empty:
            all_snapshots.append(
                snapshot
            )

    if not all_snapshots:
        raise ValueError(
            "No at-risk customer snapshots were generated."
        )

    dataset = pd.concat(
        all_snapshots,
        ignore_index=True,
    )

    dataset = dataset.sort_values(
        [
            "snapshot_date",
            "customer_id",
        ]
    ).reset_index(
        drop=True
    )

    return dataset


# ============================================================
# Validation
# ============================================================

def validate_temporal_dataset(
    dataset: pd.DataFrame,
) -> None:
    """
    Validate the temporal dataset and explicitly test
    the anti-leakage boundary.
    """

    required_columns = [
        "customer_id",
        "snapshot_date",
        "last_purchase_date",
        "days_since_last_purchase",
        "at_risk",
        "future_purchase_count",
        "future_spend",
        "recovered",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in dataset.columns
    ]

    if missing_columns:
        raise AssertionError(
            f"Missing required columns: {missing_columns}"
        )

    # Historical information must not be after snapshot.
    assert (
        dataset["last_purchase_date"]
        <= dataset["snapshot_date"]
    ).all()

    # All examples must actually be at risk.
    assert (
        dataset["at_risk"] == 1
    ).all()

    # Target must be binary.
    assert set(
        dataset["recovered"].unique()
    ).issubset({0, 1})

    # Future spend must be non-negative.
    assert (
        dataset["future_spend"] >= 0
    ).all()

    # Future purchase count must be non-negative.
    assert (
        dataset["future_purchase_count"] >= 0
    ).all()

    # Recovery label must agree with future purchases.
    assert (
        dataset["recovered"]
        == (
            dataset["future_purchase_count"] > 0
        ).astype(int)
    ).all()


# ============================================================
# Save
# ============================================================

def save_temporal_dataset(
    dataset: pd.DataFrame,
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataset.to_parquet(
        TEMPORAL_DATASET_PATH,
        index=False,
        engine="pyarrow",
    )


# ============================================================
# Main
# ============================================================

def main() -> None:

    print("=" * 60)
    print("TEMPORAL ML DATASET GENERATION")
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
    print("2. Generating temporal snapshots...")

    dataset = build_temporal_dataset(
        transactions=transactions,
        cancellations=cancellations,
    )

    print()
    print("3. Validating temporal dataset...")

    validate_temporal_dataset(
        dataset
    )

    print(
        "   [PASS] Temporal dataset validation"
    )

    print()
    print("Dataset summary:")
    print(
        f"   Rows: {len(dataset):,}"
    )

    print(
        f"   Unique customers: "
        f"{dataset['customer_id'].nunique():,}"
    )

    print(
        f"   Snapshot dates: "
        f"{dataset['snapshot_date'].nunique():,}"
    )

    print(
        f"   Recovered: "
        f"{dataset['recovered'].sum():,}"
    )

    print(
        f"   Not recovered: "
        f"{(dataset['recovered'] == 0).sum():,}"
    )

    print()
    print(
        "Recovery rate: "
        f"{dataset['recovered'].mean():.2%}"
    )

    print()
    print("4. Saving dataset...")

    save_temporal_dataset(
        dataset
    )

    print(
        f"Saved: "
        f"{TEMPORAL_DATASET_PATH}"
    )

    print()
    print("=" * 60)
    print("TEMPORAL DATASET COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()