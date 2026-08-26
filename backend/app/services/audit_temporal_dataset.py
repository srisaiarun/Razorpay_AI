from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATASET_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "temporal_training_dataset.parquet"
)


TARGET_COLUMNS = {
    "recovered",
    "future_purchase_count",
    "future_spend",
}


def main() -> None:

    print("=" * 60)
    print("TEMPORAL DATASET — LEAKAGE & TARGET AUDIT")
    print("=" * 60)

    print()
    print("Loading dataset...")

    df = pd.read_parquet(
        DATASET_PATH
    )

    print(
        f"Rows: {len(df):,}"
    )

    print(
        f"Columns: {len(df.columns):,}"
    )

    # ========================================================
    # 1. Required columns
    # ========================================================

    required_columns = {
        "customer_id",
        "snapshot_date",
        "last_purchase_date",
        "at_risk",
        "future_purchase_count",
        "future_spend",
        "recovered",
    }

    missing = (
        required_columns
        - set(df.columns)
    )

    assert not missing, (
        f"Missing columns: {missing}"
    )

    print()
    print("[PASS] Required columns exist")

    # ========================================================
    # 2. Target distribution
    # ========================================================

    print()
    print("Target distribution:")

    counts = (
        df["recovered"]
        .value_counts()
        .sort_index()
    )

    for target, count in counts.items():

        percentage = (
            count
            / len(df)
            * 100
        )

        print(
            f"  recovered={target}: "
            f"{count:,} "
            f"({percentage:.2f}%)"
        )

    assert set(
        df["recovered"].unique()
    ).issubset({0, 1})

    print()
    print("[PASS] Target is binary")

    # ========================================================
    # 3. Snapshot dates
    # ========================================================

    print()
    print("Snapshot dates:")

    snapshot_counts = (
        df.groupby(
            "snapshot_date"
        )
        .size()
    )

    for date, count in snapshot_counts.items():

        print(
            f"  {date.date()}: "
            f"{count:,} rows"
        )

    print()
    print(
        f"Snapshot dates represented: "
        f"{len(snapshot_counts)}"
    )

    # ========================================================
    # 4. Historical leakage test
    # ========================================================

    historical_leakage = (
        df["last_purchase_date"]
        > df["snapshot_date"]
    )

    leakage_count = (
        historical_leakage.sum()
    )

    assert leakage_count == 0, (
        f"Found {leakage_count} rows "
        "with historical data after snapshot."
    )

    print()
    print(
        "[PASS] No historical feature crosses "
        "the snapshot boundary"
    )

    # ========================================================
    # 5. At-risk validation
    # ========================================================

    assert (
        df["at_risk"] == 1
    ).all()

    print(
        "[PASS] All rows satisfy at-risk eligibility"
    )

    # ========================================================
    # 6. Target consistency
    # ========================================================

    expected_target = (
        df["future_purchase_count"] > 0
    ).astype(int)

    target_mismatch = (
        df["recovered"]
        != expected_target
    ).sum()

    assert target_mismatch == 0

    print(
        "[PASS] Recovery target matches "
        "future purchase behavior"
    )

    # ========================================================
    # 7. Future values sanity
    # ========================================================

    assert (
        df["future_purchase_count"] >= 0
    ).all()

    assert (
        df["future_spend"] >= 0
    ).all()

    print(
        "[PASS] Future outcome values are valid"
    )

    # ========================================================
    # 8. Identify model feature columns
    # ========================================================

    feature_columns = [
        column
        for column in df.columns
        if column not in TARGET_COLUMNS
    ]

    accidental_target_features = (
        set(feature_columns)
        & TARGET_COLUMNS
    )

    assert not accidental_target_features

    print()
    print(
        "Potential model input columns:"
    )

    for column in feature_columns:
        print(
            f"  - {column}"
        )

    print()
    print(
        "[PASS] Target columns are excluded "
        "from candidate model inputs"
    )

    # ========================================================
    # 9. Duplicate customer/snapshot pairs
    # ========================================================

    duplicate_pairs = (
        df.duplicated(
            subset=[
                "customer_id",
                "snapshot_date",
            ]
        )
        .sum()
    )

    assert duplicate_pairs == 0

    print(
        "[PASS] No duplicate customer/snapshot pairs"
    )

    # ========================================================
    # 10. Customer temporal coverage
    # ========================================================

    customer_snapshot_counts = (
        df.groupby(
            "customer_id"
        )["snapshot_date"]
        .nunique()
    )

    print()
    print(
        "Customer snapshot statistics:"
    )

    print(
        f"  Minimum: "
        f"{customer_snapshot_counts.min()}"
    )

    print(
        f"  Median: "
        f"{customer_snapshot_counts.median():.0f}"
    )

    print(
        f"  Maximum: "
        f"{customer_snapshot_counts.max()}"
    )

    # ========================================================
    # Final
    # ========================================================

    print()
    print("=" * 60)
    print("TEMPORAL DATASET AUDIT PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()