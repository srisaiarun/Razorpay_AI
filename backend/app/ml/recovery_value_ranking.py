from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_DIR = PROJECT_ROOT / "models"

VALIDATION_PATH = DATA_DIR / "ml_validation.parquet"
TEST_PATH = DATA_DIR / "ml_test.parquet"

MODEL_PATH = (
    MODEL_DIR
    / "logistic_calibrated_isotonic.joblib"
)

VALIDATION_OUTPUT = (
    DATA_DIR
    / "recovery_value_validation.parquet"
)

TEST_OUTPUT = (
    DATA_DIR
    / "recovery_value_test.parquet"
)

SUMMARY_OUTPUT = (
    DATA_DIR
    / "recovery_value_summary.csv"
)


# ============================================================
# CONFIGURATION
# ============================================================

TARGET = "recovered"

PROBABILITY_COLUMN = "recovery_probability"

AMOUNT_AT_RISK_COLUMN = "amount_at_risk"

EXPECTED_VALUE_COLUMN = "expected_recovery_value"

PRIORITY_COLUMN = "priority_score"


# ============================================================
# MODEL FEATURES
# ============================================================

FEATURE_COLUMNS = [
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


# ============================================================
# LOAD DATA
# ============================================================

def load_dataset(
    path: Path,
) -> pd.DataFrame:

    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found:\n{path}"
        )

    return pd.read_parquet(path)


# ============================================================
# VALIDATION
# ============================================================

def validate_dataset(
    df: pd.DataFrame,
    name: str,
) -> None:

    required_columns = set(
        FEATURE_COLUMNS
        + [
            TARGET,
            "customer_id",
            "snapshot_date",
        ]
    )

    missing = sorted(
        required_columns
        - set(df.columns)
    )

    if missing:
        raise ValueError(
            f"{name} is missing columns:\n"
            + "\n".join(
                f"  - {column}"
                for column in missing
            )
        )

    target_values = set(
        df[TARGET]
        .dropna()
        .unique()
    )

    if not target_values.issubset(
        {0, 1}
    ):
        raise ValueError(
            f"{name} has invalid target values: "
            f"{target_values}"
        )

    if df.empty:
        raise ValueError(
            f"{name} is empty."
        )

    print(
        f"   [PASS] {name} validation"
    )


# ============================================================
# PREDICTION
# ============================================================

def generate_probabilities(
    model,
    df: pd.DataFrame,
) -> np.ndarray:

    X = df[
        FEATURE_COLUMNS
    ].copy()

    probabilities = (
        model.predict_proba(X)[:, 1]
    )

    probabilities = np.asarray(
        probabilities,
        dtype=float,
    )

    if not np.isfinite(
        probabilities
    ).all():

        raise ValueError(
            "Model generated invalid "
            "probabilities."
        )

    probabilities = np.clip(
        probabilities,
        0.0,
        1.0,
    )

    return probabilities


# ============================================================
# AMOUNT AT RISK
# ============================================================

def calculate_amount_at_risk(
    df: pd.DataFrame,
) -> pd.Series:

    """
    First version of amount-at-risk proxy.

    Production interpretation:

        amount_at_risk =
            expected value of the customer's
            next transaction.

    Current proxy:

        average_order_value

    This is intentionally documented because the
    historical public dataset does not contain a
    real failed-payment amount.
    """

    amount = pd.to_numeric(
        df["average_order_value"],
        errors="coerce",
    )

    amount = amount.fillna(0.0)

    amount = amount.clip(
        lower=0.0
    )

    return amount


# ============================================================
# PRIORITY SCORE
# ============================================================

def calculate_priority_score(
    expected_value: pd.Series,
) -> pd.Series:

    """
    Convert expected recovery value into
    a 0-100 priority score.

    Percentile ranking is used so that the
    score is useful operationally even when
    transaction values are highly skewed.
    """

    ranks = expected_value.rank(
        method="average",
        pct=True,
    )

    return (
        ranks * 100.0
    )


# ============================================================
# BUILD RANKING
# ============================================================

def build_recovery_ranking(
    df: pd.DataFrame,
    model,
) -> pd.DataFrame:

    result = df.copy()

    # --------------------------------------------------------
    # Probability
    # --------------------------------------------------------

    result[
        PROBABILITY_COLUMN
    ] = generate_probabilities(
        model,
        result,
    )

    # --------------------------------------------------------
    # Amount at risk
    # --------------------------------------------------------

    result[
        AMOUNT_AT_RISK_COLUMN
    ] = calculate_amount_at_risk(
        result
    )

    # --------------------------------------------------------
    # Expected recovery value
    # --------------------------------------------------------

    result[
        EXPECTED_VALUE_COLUMN
    ] = (
        result[
            PROBABILITY_COLUMN
        ]
        * result[
            AMOUNT_AT_RISK_COLUMN
        ]
    )

    # --------------------------------------------------------
    # Priority
    # --------------------------------------------------------

    result[
        PRIORITY_COLUMN
    ] = calculate_priority_score(
        result[
            EXPECTED_VALUE_COLUMN
        ]
    )

    # --------------------------------------------------------
    # Rank
    # --------------------------------------------------------

    result = result.sort_values(
        [
            EXPECTED_VALUE_COLUMN,
            PROBABILITY_COLUMN,
        ],
        ascending=False,
    ).reset_index(
        drop=True
    )

    result[
        "priority_rank"
    ] = (
        result.index
        + 1
    )

    return result


# ============================================================
# SUMMARY
# ============================================================

def create_summary(
    df: pd.DataFrame,
    split_name: str,
) -> dict:

    total_customers = len(df)

    total_expected_value = (
        df[
            EXPECTED_VALUE_COLUMN
        ].sum()
    )

    total_amount_at_risk = (
        df[
            AMOUNT_AT_RISK_COLUMN
        ].sum()
    )

    actual_recovered = (
        df[TARGET].sum()
    )

    # --------------------------------------------------------
    # Top 10%
    # --------------------------------------------------------

    top_10_count = max(
        1,
        int(
            np.ceil(
                total_customers
                * 0.10
            )
        ),
    )

    top_10 = df.head(
        top_10_count
    )

    # --------------------------------------------------------
    # Top 20%
    # --------------------------------------------------------

    top_20_count = max(
        1,
        int(
            np.ceil(
                total_customers
                * 0.20
            )
        ),
    )

    top_20 = df.head(
        top_20_count
    )

    # --------------------------------------------------------
    # Actual recovery among targeted customers
    # --------------------------------------------------------

    top_10_actual_rate = (
        top_10[TARGET].mean()
    )

    top_20_actual_rate = (
        top_20[TARGET].mean()
    )

    overall_actual_rate = (
        df[TARGET].mean()
    )

    return {
        "split": split_name,
        "customers": total_customers,
        "total_amount_at_risk":
            total_amount_at_risk,
        "total_expected_recovery_value":
            total_expected_value,
        "actual_recovery_rate":
            overall_actual_rate,
        "top_10_percent_customers":
            len(top_10),
        "top_10_percent_actual_recovery_rate":
            top_10_actual_rate,
        "top_10_percent_expected_value":
            top_10[
                EXPECTED_VALUE_COLUMN
            ].sum(),
        "top_20_percent_customers":
            len(top_20),
        "top_20_percent_actual_recovery_rate":
            top_20_actual_rate,
        "top_20_percent_expected_value":
            top_20[
                EXPECTED_VALUE_COLUMN
            ].sum(),
        "actual_recovered_customers":
            int(actual_recovered),
    }


# ============================================================
# PRINT TOP CUSTOMERS
# ============================================================

def print_top_customers(
    df: pd.DataFrame,
    count: int = 20,
) -> None:

    columns = [
        "customer_id",
        "snapshot_date",
        PROBABILITY_COLUMN,
        AMOUNT_AT_RISK_COLUMN,
        EXPECTED_VALUE_COLUMN,
        PRIORITY_COLUMN,
        "priority_rank",
        TARGET,
    ]

    available = [
        column
        for column in columns
        if column in df.columns
    ]

    display = df[
        available
    ].head(count).copy()

    print()
    print(
        f"TOP {count} RECOVERY OPPORTUNITIES"
    )
    print()

    print(
        display.to_string(
            index=False,
            formatters={
                PROBABILITY_COLUMN:
                    "{:.4f}".format,
                AMOUNT_AT_RISK_COLUMN:
                    "{:.2f}".format,
                EXPECTED_VALUE_COLUMN:
                    "{:.2f}".format,
                PRIORITY_COLUMN:
                    "{:.2f}".format,
            },
        )
    )


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print("=" * 90)
    print(
        "RAZORRECOVER AI — "
        "RECOVERY VALUE RANKING"
    )
    print("=" * 90)

    # --------------------------------------------------------
    # 1. Load calibrated model
    # --------------------------------------------------------

    print()
    print(
        "1. Loading calibrated model..."
    )

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Calibrated model not found:\n"
            f"{MODEL_PATH}"
        )

    model = joblib.load(
        MODEL_PATH
    )

    print(
        f"   Loaded: {MODEL_PATH}"
    )

    # --------------------------------------------------------
    # 2. Load datasets
    # --------------------------------------------------------

    print()
    print(
        "2. Loading validation and test data..."
    )

    validation = load_dataset(
        VALIDATION_PATH
    )

    test = load_dataset(
        TEST_PATH
    )

    print(
        f"   Validation: "
        f"{len(validation):,} rows"
    )

    print(
        f"   Test: "
        f"{len(test):,} rows"
    )

    # --------------------------------------------------------
    # 3. Validate
    # --------------------------------------------------------

    print()
    print(
        "3. Validating datasets..."
    )

    validate_dataset(
        validation,
        "Validation",
    )

    validate_dataset(
        test,
        "Test",
    )

    # --------------------------------------------------------
    # 4. Build validation ranking
    # --------------------------------------------------------

    print()
    print(
        "4. Building validation recovery ranking..."
    )

    validation_ranked = (
        build_recovery_ranking(
            validation,
            model,
        )
    )

    print(
        "   [PASS] Validation ranking created"
    )

    print_top_customers(
        validation_ranked
    )

    # --------------------------------------------------------
    # 5. Build test ranking
    # --------------------------------------------------------

    print()
    print(
        "5. Building temporal test recovery ranking..."
    )

    test_ranked = (
        build_recovery_ranking(
            test,
            model,
        )
    )

    print(
        "   [PASS] Test ranking created"
    )

    print_top_customers(
        test_ranked
    )

    # --------------------------------------------------------
    # 6. Summaries
    # --------------------------------------------------------

    print()
    print(
        "6. Calculating business summaries..."
    )

    validation_summary = create_summary(
        validation_ranked,
        "validation",
    )

    test_summary = create_summary(
        test_ranked,
        "test",
    )

    summary = pd.DataFrame(
        [
            validation_summary,
            test_summary,
        ]
    )

    print()
    print(
        summary.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # 7. Save outputs
    # --------------------------------------------------------

    print()
    print(
        "7. Saving recovery rankings..."
    )

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    validation_ranked.to_parquet(
        VALIDATION_OUTPUT,
        index=False,
    )

    test_ranked.to_parquet(
        TEST_OUTPUT,
        index=False,
    )

    summary.to_csv(
        SUMMARY_OUTPUT,
        index=False,
    )

    print(
        f"   Validation: "
        f"{VALIDATION_OUTPUT}"
    )

    print(
        f"   Test: "
        f"{TEST_OUTPUT}"
    )

    print(
        f"   Summary: "
        f"{SUMMARY_OUTPUT}"
    )

    # --------------------------------------------------------
    # 8. Business interpretation
    # --------------------------------------------------------

    print()
    print("=" * 90)
    print(
        "RECOVERY VALUE RANKING COMPLETE"
    )
    print("=" * 90)

    print()

    print(
        "Ranking logic:"
    )

    print(
        "   Expected Recovery Value"
    )

    print(
        "       = calibrated recovery probability"
    )

    print(
        "       × amount at risk"
    )

    print()

    print(
        "Current amount-at-risk proxy:"
    )

    print(
        "   average_order_value"
    )

    print()

    print(
        "Production replacement:"
    )

    print(
        "   actual failed transaction amount"
    )


if __name__ == "__main__":
    main()