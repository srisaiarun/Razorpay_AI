from __future__ import annotations

from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sklearn.calibration import (
    calibration_curve,
)
from sklearn.metrics import (
    brier_score_loss,
    log_loss,
    roc_auc_score,
    average_precision_score,
)


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_DIR = PROJECT_ROOT / "models"
REPORT_DIR = PROJECT_ROOT / "data" / "reports"

VALIDATION_PATH = (
    DATA_DIR / "ml_validation.parquet"
)

TEST_PATH = (
    DATA_DIR / "ml_test.parquet"
)

MODEL_PATH = (
    MODEL_DIR / "logistic_baseline.joblib"
)

CALIBRATION_TABLE_PATH = (
    REPORT_DIR / "logistic_calibration.csv"
)

CALIBRATION_PLOT_PATH = (
    REPORT_DIR / "logistic_calibration.png"
)


# ============================================================
# TARGET
# ============================================================

TARGET = "recovered"


# ============================================================
# FEATURES
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

    if TARGET not in df.columns:
        raise ValueError(
            f"{name} does not contain "
            f"'{TARGET}'."
        )

    missing = [
        column
        for column in FEATURE_COLUMNS
        if column not in df.columns
    ]

    if missing:
        raise ValueError(
            f"{name} is missing features:\n"
            + "\n".join(
                f"  - {column}"
                for column in missing
            )
        )

    target_values = set(
        df[TARGET].dropna().unique()
    )

    if not target_values.issubset(
        {0, 1}
    ):
        raise ValueError(
            f"{name} contains invalid "
            f"target values: "
            f"{target_values}"
        )

    print(
        f"   [PASS] {name} validation"
    )


# ============================================================
# FEATURES
# ============================================================


def prepare_features(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:

    X = df[
        FEATURE_COLUMNS
    ].copy()

    y = df[
        TARGET
    ].astype(int)

    return X, y


# ============================================================
# PROBABILITY VALIDATION
# ============================================================


def validate_probabilities(
    probabilities: np.ndarray,
    name: str,
) -> None:

    if not np.isfinite(
        probabilities
    ).all():

        raise ValueError(
            f"{name} probabilities "
            "contain non-finite values."
        )

    if (
        (probabilities < 0).any()
        or (probabilities > 1).any()
    ):

        raise ValueError(
            f"{name} probabilities "
            "are outside [0, 1]."
        )


# ============================================================
# CALIBRATION TABLE
# ============================================================


def build_calibration_table(
    y_true: pd.Series,
    probabilities: np.ndarray,
    n_bins: int = 10,
) -> pd.DataFrame:

    """
    Build equal-width probability bins.

    For each bin:

        predicted_probability =
            mean predicted probability

        observed_recovery_rate =
            actual recovery rate
    """

    frame = pd.DataFrame(
        {
            "actual": y_true.to_numpy(),
            "probability": probabilities,
        }
    )

    bins = np.linspace(
        0.0,
        1.0,
        n_bins + 1,
    )

    frame["bin"] = pd.cut(
        frame["probability"],
        bins=bins,
        include_lowest=True,
        labels=False,
    )

    grouped = (
        frame.groupby(
            "bin",
            observed=False,
        )
        .agg(
            predicted_probability=(
                "probability",
                "mean",
            ),
            observed_recovery_rate=(
                "actual",
                "mean",
            ),
            customer_count=(
                "actual",
                "count",
            ),
        )
        .reset_index()
    )

    grouped["absolute_calibration_error"] = (
        grouped[
            "predicted_probability"
        ]
        - grouped[
            "observed_recovery_rate"
        ]
    ).abs()

    return grouped


# ============================================================
# CALIBRATION ERROR
# ============================================================


def calculate_expected_calibration_error(
    table: pd.DataFrame,
) -> float:

    total = table[
        "customer_count"
    ].sum()

    if total == 0:
        return 0.0

    weighted_error = (
        table[
            "absolute_calibration_error"
        ]
        * table[
            "customer_count"
        ]
    ).sum()

    return (
        weighted_error / total
    )


# ============================================================
# PRINT CALIBRATION TABLE
# ============================================================


def print_calibration_table(
    table: pd.DataFrame,
) -> None:

    print()
    print("=" * 90)
    print(
        "VALIDATION CALIBRATION TABLE"
    )
    print("=" * 90)

    print()

    display = table[
        [
            "predicted_probability",
            "observed_recovery_rate",
            "customer_count",
            "absolute_calibration_error",
        ]
    ].copy()

    print(
        display.to_string(
            index=False,
            formatters={
                "predicted_probability":
                    "{:.4f}".format,
                "observed_recovery_rate":
                    "{:.4f}".format,
                "absolute_calibration_error":
                    "{:.4f}".format,
            },
        )
    )


# ============================================================
# PLOT
# ============================================================


def save_calibration_plot(
    table: pd.DataFrame,
) -> None:

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    valid = table[
        table["customer_count"] > 0
    ].copy()

    plt.figure(
        figsize=(8, 8)
    )

    plt.plot(
        [0, 1],
        [0, 1],
        linestyle="--",
        label="Perfect calibration",
    )

    plt.plot(
        valid[
            "predicted_probability"
        ],
        valid[
            "observed_recovery_rate"
        ],
        marker="o",
        label="Logistic Regression",
    )

    plt.xlabel(
        "Mean predicted recovery probability"
    )

    plt.ylabel(
        "Observed recovery rate"
    )

    plt.title(
        "RazorRecover AI — "
        "Probability Calibration"
    )

    plt.legend()

    plt.grid(
        alpha=0.3
    )

    plt.tight_layout()

    plt.savefig(
        CALIBRATION_PLOT_PATH,
        dpi=150,
    )

    plt.close()

    print(
        f"   Saved plot: "
        f"{CALIBRATION_PLOT_PATH}"
    )


# ============================================================
# METRICS
# ============================================================


def calculate_metrics(
    y_true: pd.Series,
    probabilities: np.ndarray,
) -> dict[str, float]:

    return {
        "roc_auc": roc_auc_score(
            y_true,
            probabilities,
        ),
        "pr_auc": average_precision_score(
            y_true,
            probabilities,
        ),
        "brier_score": brier_score_loss(
            y_true,
            probabilities,
        ),
        "log_loss": log_loss(
            y_true,
            probabilities,
        ),
    }


# ============================================================
# MAIN
# ============================================================


def main() -> None:

    print("=" * 90)
    print(
        "RAZORRECOVER AI — "
        "LOGISTIC REGRESSION CALIBRATION AUDIT"
    )
    print("=" * 90)

    # --------------------------------------------------------
    # 1. Load model
    # --------------------------------------------------------

    print()
    print(
        "1. Loading Logistic Regression model..."
    )

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found:\n{MODEL_PATH}"
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
        "2. Loading validation and test datasets..."
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
    # 4. Prepare
    # --------------------------------------------------------

    print()
    print(
        "4. Preparing feature matrices..."
    )

    X_validation, y_validation = (
        prepare_features(validation)
    )

    X_test, y_test = prepare_features(
        test
    )

    print(
        f"   X_validation: "
        f"{X_validation.shape}"
    )

    print(
        f"   X_test: "
        f"{X_test.shape}"
    )

    # --------------------------------------------------------
    # 5. Generate probabilities
    # --------------------------------------------------------

    print()
    print(
        "5. Generating probabilities..."
    )

    validation_probabilities = (
        model.predict_proba(
            X_validation
        )[:, 1]
    )

    test_probabilities = (
        model.predict_proba(
            X_test
        )[:, 1]
    )

    validate_probabilities(
        validation_probabilities,
        "Validation",
    )

    validate_probabilities(
        test_probabilities,
        "Test",
    )

    print(
        "   [PASS] Probability outputs valid"
    )

    # --------------------------------------------------------
    # 6. Calculate metrics
    # --------------------------------------------------------

    print()
    print(
        "6. Calculating probability metrics..."
    )

    validation_metrics = calculate_metrics(
        y_validation,
        validation_probabilities,
    )

    test_metrics = calculate_metrics(
        y_test,
        test_probabilities,
    )

    print()
    print(
        "VALIDATION"
    )

    print(
        f"   ROC-AUC:     "
        f"{validation_metrics['roc_auc']:.4f}"
    )

    print(
        f"   PR-AUC:      "
        f"{validation_metrics['pr_auc']:.4f}"
    )

    print(
        f"   Brier Score: "
        f"{validation_metrics['brier_score']:.4f}"
    )

    print(
        f"   Log Loss:    "
        f"{validation_metrics['log_loss']:.4f}"
    )

    print()
    print(
        "TEST"
    )

    print(
        f"   ROC-AUC:     "
        f"{test_metrics['roc_auc']:.4f}"
    )

    print(
        f"   PR-AUC:      "
        f"{test_metrics['pr_auc']:.4f}"
    )

    print(
        f"   Brier Score: "
        f"{test_metrics['brier_score']:.4f}"
    )

    print(
        f"   Log Loss:    "
        f"{test_metrics['log_loss']:.4f}"
    )

    # --------------------------------------------------------
    # 7. Build calibration table
    # --------------------------------------------------------

    print()
    print(
        "7. Building validation calibration table..."
    )

    calibration_table = (
        build_calibration_table(
            y_true=y_validation,
            probabilities=validation_probabilities,
            n_bins=10,
        )
    )

    print_calibration_table(
        calibration_table
    )

    ece = (
        calculate_expected_calibration_error(
            calibration_table
        )
    )

    print()
    print(
        f"Expected Calibration Error: "
        f"{ece:.4f}"
    )

    # --------------------------------------------------------
    # 8. Save calibration data
    # --------------------------------------------------------

    print()
    print(
        "8. Saving calibration report..."
    )

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    calibration_table.to_csv(
        CALIBRATION_TABLE_PATH,
        index=False,
    )

    print(
        f"   Saved table: "
        f"{CALIBRATION_TABLE_PATH}"
    )

    save_calibration_plot(
        calibration_table
    )

    # --------------------------------------------------------
    # 9. Final summary
    # --------------------------------------------------------

    print()
    print("=" * 90)
    print(
        "CALIBRATION AUDIT COMPLETE"
    )
    print("=" * 90)

    print()
    print(
        f"Validation Brier Score: "
        f"{validation_metrics['brier_score']:.4f}"
    )

    print(
        f"Validation Log Loss: "
        f"{validation_metrics['log_loss']:.4f}"
    )

    print(
        f"Validation ECE: "
        f"{ece:.4f}"
    )

    print()
    print(
        "Interpretation:"
    )

    if ece < 0.05:
        print(
            "   [GOOD] Calibration error is low."
        )
    elif ece < 0.10:
        print(
            "   [MODERATE] Calibration may be improved."
        )
    else:
        print(
            "   [HIGH] Probability calibration "
            "needs improvement."
        )

    print()
    print("=" * 90)


if __name__ == "__main__":
    main()