from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

INPUT_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "temporal_training_dataset.parquet"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

TRAIN_PATH = (
    OUTPUT_DIR
    / "ml_train.parquet"
)

VALIDATION_PATH = (
    OUTPUT_DIR
    / "ml_validation.parquet"
)

TEST_PATH = (
    OUTPUT_DIR
    / "ml_test.parquet"
)


# ============================================================
# Columns that must never become model features
# ============================================================

EXCLUDED_COLUMNS = {
    "customer_id",
    "snapshot_date",
    "first_purchase_date",
    "last_purchase_date",
    "future_purchase_count",
    "future_spend",
    "recovered",
    "at_risk",
}


def load_dataset() -> pd.DataFrame:
    return pd.read_parquet(
        INPUT_PATH,
        engine="pyarrow",
    )


def split_by_time(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:

    dates = sorted(
        df["snapshot_date"].unique()
    )

    if len(dates) < 9:
        raise ValueError(
            "Not enough snapshot dates for "
            "train/validation/test splitting."
        )

    # --------------------------------------------------------
    # Last 6 snapshots:
    #
    #   3 validation
    #   3 test
    #
    # Everything before those becomes training.
    # --------------------------------------------------------

    validation_dates = dates[-6:-3]

    test_dates = dates[-3:]

    train_dates = dates[:-6]

    train = df[
        df["snapshot_date"].isin(
            train_dates
        )
    ].copy()

    validation = df[
        df["snapshot_date"].isin(
            validation_dates
        )
    ].copy()

    test = df[
        df["snapshot_date"].isin(
            test_dates
        )
    ].copy()

    return (
        train,
        validation,
        test,
    )


def validate_split(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
) -> None:

    # --------------------------------------------------------
    # Basic checks
    # --------------------------------------------------------

    assert not train.empty
    assert not validation.empty
    assert not test.empty

    # --------------------------------------------------------
    # Temporal ordering
    # --------------------------------------------------------

    train_max = train[
        "snapshot_date"
    ].max()

    validation_min = validation[
        "snapshot_date"
    ].min()

    validation_max = validation[
        "snapshot_date"
    ].max()

    test_min = test[
        "snapshot_date"
    ].min()

    assert train_max < validation_min

    assert validation_max < test_min

    # --------------------------------------------------------
    # No customer/snapshot duplicate
    # --------------------------------------------------------

    for name, frame in [
        ("train", train),
        ("validation", validation),
        ("test", test),
    ]:

        duplicates = frame.duplicated(
            subset=[
                "customer_id",
                "snapshot_date",
            ]
        ).sum()

        assert duplicates == 0, (
            f"{name} contains duplicate "
            "customer/snapshot pairs."
        )

    # --------------------------------------------------------
    # Target validation
    # --------------------------------------------------------

    for name, frame in [
        ("train", train),
        ("validation", validation),
        ("test", test),
    ]:

        assert set(
            frame["recovered"].unique()
        ).issubset({0, 1})

    # --------------------------------------------------------
    # Feature column validation
    # --------------------------------------------------------

    candidate_features = [
        column
        for column in train.columns
        if column not in EXCLUDED_COLUMNS
    ]

    forbidden_remaining = (
        set(candidate_features)
        & EXCLUDED_COLUMNS
    )

    assert not forbidden_remaining

    print()
    print("Candidate model features:")

    for column in candidate_features:
        print(
            f"  - {column}"
        )

    # --------------------------------------------------------
    # Critical leakage check
    # --------------------------------------------------------

    forbidden_target_columns = {
        "future_purchase_count",
        "future_spend",
        "recovered",
    }

    assert not (
        set(candidate_features)
        & forbidden_target_columns
    )

    print()
    print(
        "[PASS] No future target columns "
        "are present in model features"
    )

    print(
        "[PASS] Train occurs before validation"
    )

    print(
        "[PASS] Validation occurs before test"
    )


def save_split(
    df: pd.DataFrame,
    path: Path,
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_parquet(
        path,
        index=False,
        engine="pyarrow",
    )


def print_split_summary(
    name: str,
    df: pd.DataFrame,
) -> None:

    recovery_rate = (
        df["recovered"].mean()
    )

    print()
    print(
        f"{name}:"
    )

    print(
        f"  Rows: {len(df):,}"
    )

    print(
        f"  Customers: "
        f"{df['customer_id'].nunique():,}"
    )

    print(
        f"  Snapshots: "
        f"{df['snapshot_date'].nunique():,}"
    )

    print(
        f"  Start: "
        f"{df['snapshot_date'].min().date()}"
    )

    print(
        f"  End: "
        f"{df['snapshot_date'].max().date()}"
    )

    print(
        f"  Recovered: "
        f"{df['recovered'].sum():,}"
    )

    print(
        f"  Recovery rate: "
        f"{recovery_rate:.2%}"
    )


def main() -> None:

    print("=" * 60)
    print("TEMPORAL TRAIN / VALIDATION / TEST SPLIT")
    print("=" * 60)

    print()
    print("Loading dataset...")

    df = load_dataset()

    print(
        f"Total rows: "
        f"{len(df):,}"
    )

    train, validation, test = (
        split_by_time(df)
    )

    print()
    print("Validating splits...")

    validate_split(
        train,
        validation,
        test,
    )

    print()
    print_split_summary(
        "TRAIN",
        train,
    )

    print_split_summary(
        "VALIDATION",
        validation,
    )

    print_split_summary(
        "TEST",
        test,
    )

    print()
    print("Saving splits...")

    save_split(
        train,
        TRAIN_PATH,
    )

    save_split(
        validation,
        VALIDATION_PATH,
    )

    save_split(
        test,
        TEST_PATH,
    )

    print()
    print(
        f"Train: {TRAIN_PATH}"
    )

    print(
        f"Validation: {VALIDATION_PATH}"
    )

    print(
        f"Test: {TEST_PATH}"
    )

    print()
    print("=" * 60)
    print("ML DATASET SPLIT COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()