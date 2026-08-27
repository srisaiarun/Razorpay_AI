from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

VALIDATION_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "recovery_value_validation.parquet"
)

TEST_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "recovery_value_test.parquet"
)

POLICY_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "decision_policy_evaluation.csv"
)

SELECTED_POLICY_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "selected_decision_policy.csv"
)


REQUIRED_COLUMNS = {
    "customer_id",
    "snapshot_date",
    "recovery_probability",
    "amount_at_risk",
    "expected_recovery_value",
    "recovered",
}


TARGET_PERCENTAGES = [
    0.05,
    0.10,
    0.15,
    0.20,
    0.25,
    0.30,
    0.40,
    0.50,
]


def validate_dataset(df: pd.DataFrame, name: str) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)

    if missing:
        raise ValueError(
            f"{name} is missing required columns: "
            f"{sorted(missing)}"
        )

    if df.empty:
        raise ValueError(f"{name} is empty.")

    if df["recovery_probability"].isna().any():
        raise ValueError(
            f"{name} contains missing recovery probabilities."
        )

    if df["expected_recovery_value"].isna().any():
        raise ValueError(
            f"{name} contains missing expected recovery values."
        )

    if not set(df["recovered"].unique()).issubset({0, 1}):
        raise ValueError(
            f"{name} recovered target must be binary."
        )

    if (df["recovery_probability"] < 0).any():
        raise ValueError(
            f"{name} contains probabilities below 0."
        )

    if (df["recovery_probability"] > 1).any():
        raise ValueError(
            f"{name} contains probabilities above 1."
        )

    if (df["amount_at_risk"] < 0).any():
        raise ValueError(
            f"{name} contains negative amount-at-risk values."
        )

    if (df["expected_recovery_value"] < 0).any():
        raise ValueError(
            f"{name} contains negative expected recovery values."
        )


def select_latest_customer_snapshot(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Keep only the latest opportunity for every customer.

    This prevents the same customer from appearing multiple
    times in the operational queue.
    """

    result = df.copy()

    result["snapshot_date"] = pd.to_datetime(
        result["snapshot_date"],
        errors="coerce",
    )

    result = result.sort_values(
        ["customer_id", "snapshot_date"]
    )

    result = (
        result
        .groupby("customer_id", as_index=False)
        .tail(1)
        .reset_index(drop=True)
    )

    return result


def calculate_random_baseline(
    df: pd.DataFrame,
    target_count: int,
) -> float:
    """
    Expected recovery rate from randomly targeting customers.

    This is the benchmark against which targeted policies
    are compared.
    """

    if target_count <= 0:
        return 0.0

    if target_count >= len(df):
        return float(df["recovered"].mean())

    return float(df["recovered"].mean())


def evaluate_target_percentage(
    df: pd.DataFrame,
    percentage: float,
) -> dict:
    """
    Evaluate a top-X%-of-customers targeting policy.

    Ranking is based on expected recovery value.
    """

    ranked = df.sort_values(
        [
            "expected_recovery_value",
            "recovery_probability",
            "amount_at_risk",
        ],
        ascending=[False, False, False],
    ).reset_index(drop=True)

    total_customers = len(ranked)

    target_count = max(
        1,
        int(np.ceil(total_customers * percentage)),
    )

    targeted = ranked.iloc[:target_count].copy()

    non_targeted = ranked.iloc[target_count:].copy()

    total_recovered = int(targeted["recovered"].sum())

    targeted_recovery_rate = float(
        targeted["recovered"].mean()
    )

    overall_recovery_rate = float(
        ranked["recovered"].mean()
    )

    baseline_recovery_rate = calculate_random_baseline(
        ranked,
        target_count,
    )

    if baseline_recovery_rate > 0:
        recovery_lift = (
            targeted_recovery_rate
            / baseline_recovery_rate
        )
    else:
        recovery_lift = np.nan

    total_expected_value = float(
        targeted["expected_recovery_value"].sum()
    )

    total_amount_at_risk = float(
        targeted["amount_at_risk"].sum()
    )

    total_actual_recovered_value = float(
        targeted.loc[
            targeted["recovered"] == 1,
            "amount_at_risk",
        ].sum()
    )

    expected_value_capture = (
        total_expected_value
        / max(
            float(ranked["expected_recovery_value"].sum()),
            1e-9,
        )
    )

    actual_recovery_capture = (
        total_recovered
        / max(
            int(ranked["recovered"].sum()),
            1,
        )
    )

    return {
        "target_percentage": percentage,
        "targeted_customers": target_count,
        "target_rate": target_count / total_customers,
        "targeted_recovery_rate": targeted_recovery_rate,
        "overall_recovery_rate": overall_recovery_rate,
        "baseline_recovery_rate": baseline_recovery_rate,
        "recovery_lift": recovery_lift,
        "recovered_customers": total_recovered,
        "total_expected_recovery_value": total_expected_value,
        "total_amount_at_risk": total_amount_at_risk,
        "actual_recovered_amount": total_actual_recovered_value,
        "expected_value_capture": expected_value_capture,
        "actual_recovery_capture": actual_recovery_capture,
        "non_targeted_customers": len(non_targeted),
    }


def build_policy_evaluation(
    validation: pd.DataFrame,
) -> pd.DataFrame:

    results = []

    for percentage in TARGET_PERCENTAGES:
        result = evaluate_target_percentage(
            validation,
            percentage,
        )

        results.append(result)

    return pd.DataFrame(results)


def select_policy(
    evaluation: pd.DataFrame,
) -> pd.Series:
    """
    Select policy using validation data only.

    Primary objective:
        maximize expected recovery value per targeted customer.

    Secondary objective:
        maximize recovery lift.

    We deliberately do NOT inspect the test set here.
    """

    candidates = evaluation.copy()

    candidates["expected_value_per_target"] = (
        candidates["total_expected_recovery_value"]
        / candidates["targeted_customers"]
    )

    candidates = candidates.sort_values(
        [
            "expected_value_per_target",
            "recovery_lift",
            "target_percentage",
        ],
        ascending=[False, False, True],
    )

    return candidates.iloc[0]


def evaluate_locked_policy(
    df: pd.DataFrame,
    selected_percentage: float,
) -> dict:

    return evaluate_target_percentage(
        df,
        selected_percentage,
    )


def main() -> None:

    print("=" * 90)
    print("RAZORRECOVER AI — DECISION POLICY OPTIMIZATION")
    print("=" * 90)

    # ---------------------------------------------------------
    # 1. Load datasets
    # ---------------------------------------------------------

    print()
    print("1. Loading recovery-value rankings...")

    validation = pd.read_parquet(
        VALIDATION_PATH
    )

    test = pd.read_parquet(
        TEST_PATH
    )

    print(
        f"   Validation opportunities: {len(validation):,}"
    )

    print(
        f"   Test opportunities:       {len(test):,}"
    )

    # ---------------------------------------------------------
    # 2. Validate
    # ---------------------------------------------------------

    print()
    print("2. Validating datasets...")

    validate_dataset(
        validation,
        "Validation",
    )

    validate_dataset(
        test,
        "Test",
    )

    print("   [PASS] Validation validation")
    print("   [PASS] Test validation")

    # ---------------------------------------------------------
    # 3. Customer-level latest snapshot
    # ---------------------------------------------------------

    print()
    print("3. Selecting latest customer opportunity...")

    validation_customers = (
        select_latest_customer_snapshot(
            validation
        )
    )

    test_customers = (
        select_latest_customer_snapshot(
            test
        )
    )

    print(
        f"   Validation customers: "
        f"{len(validation_customers):,}"
    )

    print(
        f"   Test customers:       "
        f"{len(test_customers):,}"
    )

    # ---------------------------------------------------------
    # 4. Validation policy search
    # ---------------------------------------------------------

    print()
    print(
        "4. Searching targeting policies using "
        "validation data only..."
    )

    evaluation = build_policy_evaluation(
        validation_customers
    )

    print()
    print("=" * 90)
    print("VALIDATION POLICY EVALUATION")
    print("=" * 90)

    display_columns = [
        "target_percentage",
        "targeted_customers",
        "targeted_recovery_rate",
        "recovery_lift",
        "recovered_customers",
        "total_expected_recovery_value",
        "expected_value_capture",
        "actual_recovery_capture",
    ]

    print(
        evaluation[
            display_columns
        ].to_string(
            index=False,
            formatters={
                "target_percentage": "{:.0%}".format,
                "targeted_recovery_rate": "{:.4f}".format,
                "recovery_lift": "{:.3f}x".format,
                "expected_value_capture": "{:.4f}".format,
                "actual_recovery_capture": "{:.4f}".format,
                "total_expected_recovery_value": (
                    "{:,.2f}".format
                ),
            },
        )
    )

    # ---------------------------------------------------------
    # 5. Select policy
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("SELECTED VALIDATION POLICY")
    print("=" * 90)

    selected = select_policy(
        evaluation
    )

    selected_percentage = float(
        selected["target_percentage"]
    )

    print(
        f"Target percentage: "
        f"{selected_percentage:.0%}"
    )

    print(
        f"Targeted customers: "
        f"{int(selected['targeted_customers']):,}"
    )

    print(
        f"Validation recovery rate: "
        f"{selected['targeted_recovery_rate']:.4f}"
    )

    print(
        f"Validation recovery lift: "
        f"{selected['recovery_lift']:.3f}x"
    )

    print(
        f"Validation expected recovery value: "
        f"£{selected['total_expected_recovery_value']:,.2f}"
    )

    print(
        "[PASS] Policy selected using validation only"
    )

    # ---------------------------------------------------------
    # 6. Lock policy
    # ---------------------------------------------------------

    locked_policy = pd.DataFrame(
        [
            {
                "policy_name": (
                    "TOP_EXPECTED_RECOVERY_VALUE"
                ),
                "target_percentage": (
                    selected_percentage
                ),
                "selection_basis": (
                    "validation_only"
                ),
                "ranking_metric": (
                    "expected_recovery_value"
                ),
            }
        ]
    )

    # ---------------------------------------------------------
    # 7. Evaluate locked policy on test
    # ---------------------------------------------------------

    print()
    print(
        "5. Locking policy before test evaluation..."
    )

    print(
        f"   Locked targeting rate: "
        f"{selected_percentage:.0%}"
    )

    print(
        "   [PASS] Test data not used for policy selection"
    )

    test_result = evaluate_locked_policy(
        test_customers,
        selected_percentage,
    )

    print()
    print("=" * 90)
    print("FINAL TEST RESULTS — LOCKED DECISION POLICY")
    print("=" * 90)

    print(
        f"Target percentage: "
        f"{selected_percentage:.0%}"
    )

    print(
        f"Targeted customers: "
        f"{test_result['targeted_customers']:,}"
    )

    print(
        f"Targeted recovery rate: "
        f"{test_result['targeted_recovery_rate']:.4f}"
    )

    print(
        f"Overall recovery rate: "
        f"{test_result['overall_recovery_rate']:.4f}"
    )

    print(
        f"Recovery lift: "
        f"{test_result['recovery_lift']:.3f}x"
    )

    print(
        f"Recovered customers: "
        f"{test_result['recovered_customers']:,}"
    )

    print(
        f"Expected recovery value: "
        f"£{test_result['total_expected_recovery_value']:,.2f}"
    )

    print(
        f"Actual recovered amount at risk: "
        f"£{test_result['actual_recovered_amount']:,.2f}"
    )

    print(
        f"Expected value captured: "
        f"{test_result['expected_value_capture']:.2%}"
    )

    print(
        f"Actual recovery captured: "
        f"{test_result['actual_recovery_capture']:.2%}"
    )

    # ---------------------------------------------------------
    # 8. Save reports
    # ---------------------------------------------------------

    print()
    print("6. Saving policy evaluation...")

    POLICY_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    evaluation.to_csv(
        POLICY_PATH,
        index=False,
    )

    locked_policy.to_csv(
        SELECTED_POLICY_PATH,
        index=False,
    )

    print(
        f"   Evaluation: {POLICY_PATH}"
    )

    print(
        f"   Selected policy: "
        f"{SELECTED_POLICY_PATH}"
    )

    # ---------------------------------------------------------
    # 9. Final summary
    # ---------------------------------------------------------

    print()
    print("=" * 90)
    print("DECISION POLICY OPTIMIZATION COMPLETE")
    print("=" * 90)

    print()
    print("Locked policy:")
    print(
        "   Rank customers by expected recovery value"
    )
    print(
        f"   Target top {selected_percentage:.0%}"
    )
    print(
        "   Policy selected using validation data only"
    )
    print(
        "   Evaluate locked policy on future/test data"
    )

    print()
    print(
        "Operational interpretation:"
    )

    print(
        "   Expected recovery value"
    )
    print(
        "          ↓"
    )
    print(
        "   Customer ranking"
    )
    print(
        "          ↓"
    )
    print(
        "   Capacity-constrained targeting"
    )
    print(
        "          ↓"
    )
    print(
        "   Recovery queue"
    )

    print()
    print("=" * 90)


if __name__ == "__main__":
    main()