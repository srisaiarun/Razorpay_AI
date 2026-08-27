from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data" / "processed"

INPUT_PATH = (
    DATA_DIR
    / "recovery_value_test.parquet"
)

OUTPUT_PATH = (
    DATA_DIR
    / "customer_recovery_queue.parquet"
)

SUMMARY_PATH = (
    DATA_DIR
    / "customer_recovery_queue_summary.csv"
)


# ============================================================
# CONFIGURATION
# ============================================================

CUSTOMER_ID = "customer_id"
SNAPSHOT_DATE = "snapshot_date"

PROBABILITY = "recovery_probability"
AMOUNT_AT_RISK = "amount_at_risk"
EXPECTED_VALUE = "expected_recovery_value"

PRIORITY_SCORE = "priority_score"
PRIORITY_RANK = "priority_rank"


# ============================================================
# VALIDATION
# ============================================================

REQUIRED_COLUMNS = {
    CUSTOMER_ID,
    SNAPSHOT_DATE,
    PROBABILITY,
    AMOUNT_AT_RISK,
    EXPECTED_VALUE,
    PRIORITY_SCORE,
    PRIORITY_RANK,
}


def validate_input(
    df: pd.DataFrame,
) -> None:

    missing = sorted(
        REQUIRED_COLUMNS
        - set(df.columns)
    )

    if missing:
        raise ValueError(
            "Input dataset is missing required "
            "columns:\n"
            + "\n".join(
                f"  - {column}"
                for column in missing
            )
        )

    if df.empty:
        raise ValueError(
            "Input dataset is empty."
        )

    if df[CUSTOMER_ID].isna().any():
        raise ValueError(
            "Customer IDs contain missing values."
        )

    if df[SNAPSHOT_DATE].isna().any():
        raise ValueError(
            "Snapshot dates contain missing values."
        )

    if (
        ~np.isfinite(
            df[PROBABILITY]
            .astype(float)
        )
    ).any():

        raise ValueError(
            "Recovery probabilities contain "
            "invalid values."
        )

    if (
        (df[PROBABILITY] < 0)
        | (df[PROBABILITY] > 1)
    ).any():

        raise ValueError(
            "Recovery probabilities must be "
            "between 0 and 1."
        )

    if (
        df[AMOUNT_AT_RISK]
        .astype(float)
        < 0
    ).any():

        raise ValueError(
            "Amount at risk cannot be negative."
        )

    if (
        df[EXPECTED_VALUE]
        .astype(float)
        < 0
    ).any():

        raise ValueError(
            "Expected recovery value cannot "
            "be negative."
        )

    print(
        "   [PASS] Input validation"
    )


# ============================================================
# LATEST SNAPSHOT
# ============================================================

def select_latest_customer_snapshot(
    df: pd.DataFrame,
) -> pd.DataFrame:

    result = df.copy()

    result[SNAPSHOT_DATE] = pd.to_datetime(
        result[SNAPSHOT_DATE],
        errors="raise",
    )

    # Latest observation for every customer.
    result = (
        result.sort_values(
            [
                CUSTOMER_ID,
                SNAPSHOT_DATE,
            ]
        )
        .drop_duplicates(
            subset=[CUSTOMER_ID],
            keep="last",
        )
        .reset_index(drop=True)
    )

    if result[CUSTOMER_ID].duplicated().any():
        raise ValueError(
            "Customer-level queue contains "
            "duplicate customers."
        )

    print(
        "   [PASS] One latest snapshot "
        "per customer"
    )

    return result


# ============================================================
# RISK BAND
# ============================================================

def assign_risk_band(
    probability: pd.Series,
) -> pd.Series:

    """
    Risk/recovery bands are based on calibrated
    recovery probability.

    HIGH:
        >= 0.70

    MEDIUM:
        >= 0.40 and < 0.70

    LOW:
        >= 0.20 and < 0.40

    VERY_LOW:
        < 0.20
    """

    return pd.cut(
        probability,
        bins=[
            -np.inf,
            0.20,
            0.40,
            0.70,
            np.inf,
        ],
        labels=[
            "VERY_LOW",
            "LOW",
            "MEDIUM",
            "HIGH",
        ],
        right=False,
    ).astype("string")


# ============================================================
# PRIORITY BAND
# ============================================================

def assign_priority_band(
    expected_value: pd.Series,
) -> pd.Series:

    """
    Business-value bands.

    The thresholds are intentionally based on
    expected recovery value rather than only
    probability.

    They can later be replaced by learned
    validation-based thresholds.
    """

    return pd.cut(
        expected_value,
        bins=[
            -np.inf,
            100.0,
            500.0,
            1000.0,
            2500.0,
            np.inf,
        ],
        labels=[
            "P5_LOW",
            "P4",
            "P3",
            "P2",
            "P1_HIGH",
        ],
        right=False,
    ).astype("string")


# ============================================================
# ACTION RECOMMENDATION
# ============================================================

def recommend_action(
    probability: pd.Series,
    expected_value: pd.Series,
) -> pd.Series:

    """
    Initial deterministic policy.

    The ML model supplies probability and value.
    The policy translates those signals into
    an operational recommendation.

    This is intentionally NOT the final agent.
    """

    conditions = [
        (
            (probability >= 0.70)
            & (expected_value >= 1000)
        ),
        (
            (probability >= 0.50)
            & (expected_value >= 500)
        ),
        (
            (probability >= 0.30)
            & (expected_value >= 100)
        ),
        (
            (probability >= 0.20)
            | (expected_value >= 100)
        ),
    ]

    choices = [
        "HIGH_PRIORITY_RECOVERY",
        "STANDARD_RECOVERY",
        "LOW_COST_RECOVERY",
        "MONITOR",
    ]

    return pd.Series(
        np.select(
            conditions,
            choices,
            default="NO_ACTION",
        ),
        index=probability.index,
        dtype="string",
    )


# ============================================================
# QUEUE SCORE
# ============================================================

def calculate_queue_score(
    probability: pd.Series,
    expected_value: pd.Series,
) -> pd.Series:

    """
    Operational queue score.

    Expected value is the primary business signal.

    Probability provides a secondary signal so
    extremely uncertain high-value opportunities
    do not automatically dominate.

    Score is normalized to 0-100.
    """

    value_log = np.log1p(
        expected_value.clip(
            lower=0
        )
    )

    max_value = value_log.max()

    if max_value <= 0:
        normalized_value = pd.Series(
            0.0,
            index=expected_value.index,
        )
    else:
        normalized_value = (
            value_log
            / max_value
        )

    score = (
        0.70 * normalized_value
        + 0.30 * probability
    )

    return (
        score
        * 100.0
    )


# ============================================================
# BUILD QUEUE
# ============================================================

def build_queue(
    df: pd.DataFrame,
) -> pd.DataFrame:

    result = (
        select_latest_customer_snapshot(
            df
        )
    )

    # --------------------------------------------------------
    # Risk classification
    # --------------------------------------------------------

    result[
        "recovery_risk_band"
    ] = assign_risk_band(
        result[PROBABILITY]
    )

    # --------------------------------------------------------
    # Business priority
    # --------------------------------------------------------

    result[
        "priority_band"
    ] = assign_priority_band(
        result[EXPECTED_VALUE]
    )

    # --------------------------------------------------------
    # Recommended action
    # --------------------------------------------------------

    result[
        "recommended_action"
    ] = recommend_action(
        result[PROBABILITY],
        result[EXPECTED_VALUE],
    )

    # --------------------------------------------------------
    # Queue score
    # --------------------------------------------------------

    result[
        "queue_score"
    ] = calculate_queue_score(
        result[PROBABILITY],
        result[EXPECTED_VALUE],
    )

    # --------------------------------------------------------
    # Sort highest priority first
    # --------------------------------------------------------

    result = result.sort_values(
        [
            "queue_score",
            EXPECTED_VALUE,
            PROBABILITY,
        ],
        ascending=False,
    ).reset_index(
        drop=True
    )

    result[
        "queue_rank"
    ] = (
        result.index
        + 1
    )

    # --------------------------------------------------------
    # Agent-facing columns
    # --------------------------------------------------------

    preferred_columns = [
        CUSTOMER_ID,
        SNAPSHOT_DATE,
        PROBABILITY,
        AMOUNT_AT_RISK,
        EXPECTED_VALUE,
        PRIORITY_SCORE,
        "queue_score",
        "queue_rank",
        "recovery_risk_band",
        "priority_band",
        "recommended_action",
        "purchase_count",
        "total_spend",
        "average_order_value",
        "days_since_last_purchase",
        "cancellation_rate",
        "recovered",
    ]

    available_columns = [
        column
        for column in preferred_columns
        if column in result.columns
    ]

    return result[
        available_columns
    ].copy()


# ============================================================
# VALIDATE QUEUE
# ============================================================

def validate_queue(
    queue: pd.DataFrame,
) -> None:

    if queue.empty:
        raise ValueError(
            "Recovery queue is empty."
        )

    if queue[CUSTOMER_ID].duplicated().any():
        raise ValueError(
            "Recovery queue contains duplicate "
            "customers."
        )

    if not queue[
        "queue_score"
    ].between(
        0,
        100,
    ).all():

        raise ValueError(
            "Queue scores must be between "
            "0 and 100."
        )

    if not queue[
        "queue_rank"
    ].is_monotonic_increasing:

        raise ValueError(
            "Queue ranks are not sequential."
        )

    if queue[
        EXPECTED_VALUE
    ].isna().any():

        raise ValueError(
            "Expected recovery values contain "
            "missing values."
        )

    if queue[
        "recommended_action"
    ].isna().any():

        raise ValueError(
            "Recommended actions contain "
            "missing values."
        )

    print(
        "   [PASS] Queue validation"
    )


# ============================================================
# SUMMARY
# ============================================================

def create_summary(
    queue: pd.DataFrame,
) -> pd.DataFrame:

    total = len(queue)

    summary_rows = []

    for action, group in queue.groupby(
        "recommended_action",
        dropna=False,
    ):

        summary_rows.append(
            {
                "recommended_action": action,
                "customers": len(group),
                "percentage_of_queue":
                    (
                        len(group)
                        / total
                        * 100
                    ),
                "total_expected_recovery":
                    group[
                        EXPECTED_VALUE
                    ].sum(),
                "average_probability":
                    group[
                        PROBABILITY
                    ].mean(),
                "actual_recovery_rate":
                    group[
                        "recovered"
                    ].mean(),
            }
        )

    return (
        pd.DataFrame(
            summary_rows
        )
        .sort_values(
            "total_expected_recovery",
            ascending=False,
        )
        .reset_index(
            drop=True
        )
    )


# ============================================================
# PRINT TOP QUEUE
# ============================================================

def print_top_queue(
    queue: pd.DataFrame,
    count: int = 25,
) -> None:

    columns = [
        CUSTOMER_ID,
        SNAPSHOT_DATE,
        PROBABILITY,
        AMOUNT_AT_RISK,
        EXPECTED_VALUE,
        "queue_score",
        "queue_rank",
        "recovery_risk_band",
        "priority_band",
        "recommended_action",
        "recovered",
    ]

    display = queue[
        columns
    ].head(count).copy()

    print()
    print(
        f"TOP {count} CUSTOMER RECOVERY QUEUE"
    )
    print()

    print(
        display.to_string(
            index=False,
            formatters={
                PROBABILITY:
                    "{:.4f}".format,
                AMOUNT_AT_RISK:
                    "{:.2f}".format,
                EXPECTED_VALUE:
                    "{:.2f}".format,
                "queue_score":
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
        "CUSTOMER RECOVERY QUEUE"
    )
    print("=" * 90)

    # --------------------------------------------------------
    # 1. Load recovery ranking
    # --------------------------------------------------------

    print()
    print(
        "1. Loading recovery-value ranking..."
    )

    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"Input file not found:\n"
            f"{INPUT_PATH}"
        )

    df = pd.read_parquet(
        INPUT_PATH
    )

    print(
        f"   Input rows: "
        f"{len(df):,}"
    )

    # --------------------------------------------------------
    # 2. Validate
    # --------------------------------------------------------

    print()
    print(
        "2. Validating input..."
    )

    validate_input(
        df
    )

    # --------------------------------------------------------
    # 3. Build customer queue
    # --------------------------------------------------------

    print()
    print(
        "3. Building customer-level queue..."
    )

    queue = build_queue(
        df
    )

    print(
        f"   Temporal opportunities: "
        f"{len(df):,}"
    )

    print(
        f"   Unique customers: "
        f"{len(queue):,}"
    )

    print(
        f"   Opportunities removed by "
        f"latest-snapshot selection: "
        f"{len(df) - len(queue):,}"
    )

    # --------------------------------------------------------
    # 4. Validate queue
    # --------------------------------------------------------

    print()
    print(
        "4. Validating customer queue..."
    )

    validate_queue(
        queue
    )

    # --------------------------------------------------------
    # 5. Display
    # --------------------------------------------------------

    print()
    print(
        "5. Inspecting highest-priority customers..."
    )

    print_top_queue(
        queue
    )

    # --------------------------------------------------------
    # 6. Summary
    # --------------------------------------------------------

    print()
    print(
        "6. Creating action summary..."
    )

    summary = create_summary(
        queue
    )

    print()
    print(
        summary.to_string(
            index=False
        )
    )

    # --------------------------------------------------------
    # 7. Save
    # --------------------------------------------------------

    print()
    print(
        "7. Saving customer recovery queue..."
    )

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    queue.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    summary.to_csv(
        SUMMARY_PATH,
        index=False,
    )

    print(
        f"   Queue: "
        f"{OUTPUT_PATH}"
    )

    print(
        f"   Summary: "
        f"{SUMMARY_PATH}"
    )

    # --------------------------------------------------------
    # 8. Final checks
    # --------------------------------------------------------

    print()
    print("=" * 90)
    print(
        "CUSTOMER RECOVERY QUEUE COMPLETE"
    )
    print("=" * 90)

    print()
    print(
        "Operational flow:"
    )

    print(
        "   Temporal predictions"
    )

    print(
        "        ↓"
    )

    print(
        "   Recovery value"
    )

    print(
        "        ↓"
    )

    print(
        "   Latest customer snapshot"
    )

    print(
        "        ↓"
    )

    print(
        "   Priority + risk bands"
    )

    print(
        "        ↓"
    )

    print(
        "   Recommended recovery action"
    )


if __name__ == "__main__":
    main()