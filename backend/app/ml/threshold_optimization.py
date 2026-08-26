from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_DIR = PROJECT_ROOT / "models"

VALIDATION_PATH = DATA_DIR / "ml_validation.parquet"
TEST_PATH = DATA_DIR / "ml_test.parquet"

MODEL_PATH = MODEL_DIR / "logistic_baseline.joblib"

RESULTS_PATH = (
    DATA_DIR / "threshold_evaluation.csv"
)


# ============================================================
# TARGET
# ============================================================

TARGET = "recovered"


# ============================================================
# APPROVED MODEL FEATURES
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
# THRESHOLDS
# ============================================================

THRESHOLDS = np.round(
    np.arange(
        0.10,
        0.91,
        0.05,
    ),
    2,
)


# ============================================================
# DATA LOADING
# ============================================================


def load_dataset(
    path: Path,
) -> pd.DataFrame:
    """Load an ML split."""

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
    """Validate target and feature availability."""

    if TARGET not in df.columns:
        raise ValueError(
            f"{name} is missing target "
            f"column '{TARGET}'."
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

    if not target_values.issubset({0, 1}):
        raise ValueError(
            f"{name} contains invalid target "
            f"values: {target_values}"
        )

    print(
        f"   [PASS] {name} validation"
    )


# ============================================================
# FEATURE MATRIX
# ============================================================


def prepare_features(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    """Prepare features and target."""

    X = df[
        FEATURE_COLUMNS
    ].copy()

    y = df[
        TARGET
    ].astype(int)

    return X, y


# ============================================================
# MODEL PROBABILITIES
# ============================================================


def predict_probabilities(
    model,
    X: pd.DataFrame,
) -> np.ndarray:
    """Generate positive-class probabilities."""

    probabilities = model.predict_proba(
        X
    )[:, 1]

    if not np.isfinite(
        probabilities
    ).all():
        raise ValueError(
            "Model produced non-finite "
            "probabilities."
        )

    if (
        (probabilities < 0).any()
        or (probabilities > 1).any()
    ):
        raise ValueError(
            "Model produced probabilities "
            "outside [0, 1]."
        )

    return probabilities


# ============================================================
# THRESHOLD EVALUATION
# ============================================================


def evaluate_threshold(
    y_true: pd.Series,
    probabilities: np.ndarray,
    threshold: float,
) -> dict[str, float]:

    predictions = (
        probabilities >= threshold
    ).astype(int)

    tn, fp, fn, tp = confusion_matrix(
        y_true,
        predictions,
        labels=[0, 1],
    ).ravel()

    precision = precision_score(
        y_true,
        predictions,
        zero_division=0,
    )

    recall = recall_score(
        y_true,
        predictions,
        zero_division=0,
    )

    f1 = f1_score(
        y_true,
        predictions,
        zero_division=0,
    )

    targeted = int(
        predictions.sum()
    )

    total = len(predictions)

    target_rate = (
        targeted / total
        if total
        else 0.0
    )

    return {
        "threshold": threshold,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_negatives": tn,
        "false_positives": fp,
        "false_negatives": fn,
        "true_positives": tp,
        "targeted_customers": targeted,
        "target_rate": target_rate,
    }


# ============================================================
# VALIDATION THRESHOLD SEARCH
# ============================================================


def evaluate_validation_thresholds(
    y_validation: pd.Series,
    validation_probabilities: np.ndarray,
) -> pd.DataFrame:

    results = []

    for threshold in THRESHOLDS:

        metrics = evaluate_threshold(
            y_true=y_validation,
            probabilities=validation_probabilities,
            threshold=float(threshold),
        )

        results.append(metrics)

    return pd.DataFrame(results)


# ============================================================
# SELECT THRESHOLD
# ============================================================


def select_best_threshold(
    results: pd.DataFrame,
) -> pd.Series:
    """
    Select threshold using validation F1.

    Test data is intentionally NOT used here.
    """

    best = (
        results.sort_values(
            [
                "f1",
                "precision",
                "recall",
            ],
            ascending=False,
        )
        .iloc[0]
    )

    return best


# ============================================================
# PRINT VALIDATION RESULTS
# ============================================================


def print_validation_results(
    results: pd.DataFrame,
) -> None:

    print()
    print("=" * 80)
    print(
        "VALIDATION THRESHOLD ANALYSIS"
    )
    print("=" * 80)

    print()

    print(
        results[
            [
                "threshold",
                "precision",
                "recall",
                "f1",
                "targeted_customers",
                "target_rate",
            ]
        ].to_string(
            index=False,
            formatters={
                "threshold": "{:.2f}".format,
                "precision": "{:.4f}".format,
                "recall": "{:.4f}".format,
                "f1": "{:.4f}".format,
                "target_rate": "{:.2%}".format,
            },
        )
    )


# ============================================================
# TEST EVALUATION
# ============================================================


def evaluate_locked_threshold(
    y_test: pd.Series,
    test_probabilities: np.ndarray,
    threshold: float,
) -> dict[str, float]:

    metrics = evaluate_threshold(
        y_true=y_test,
        probabilities=test_probabilities,
        threshold=threshold,
    )

    return metrics


# ============================================================
# MAIN
# ============================================================


def main() -> None:

    print("=" * 80)
    print(
        "RAZORRECOVER AI — "
        "VALIDATION THRESHOLD OPTIMIZATION"
    )
    print("=" * 80)

    # --------------------------------------------------------
    # 1. Load model
    # --------------------------------------------------------

    print()
    print("1. Loading Logistic Regression model...")

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
    # 2. Load validation and test datasets
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
        f"   Test:       "
        f"{len(test):,} rows"
    )

    # --------------------------------------------------------
    # 3. Validate datasets
    # --------------------------------------------------------

    print()
    print("3. Validating datasets...")

    validate_dataset(
        validation,
        "Validation",
    )

    validate_dataset(
        test,
        "Test",
    )

    # --------------------------------------------------------
    # 4. Prepare features
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
        "5. Generating model probabilities..."
    )

    validation_probabilities = (
        predict_probabilities(
            model,
            X_validation,
        )
    )

    test_probabilities = (
        predict_probabilities(
            model,
            X_test,
        )
    )

    print(
        "   [PASS] Validation probabilities generated"
    )

    print(
        "   [PASS] Test probabilities generated"
    )

    # --------------------------------------------------------
    # 6. Calculate ranking metrics
    # --------------------------------------------------------

    print()
    print(
        "6. Calculating threshold-independent metrics..."
    )

    validation_roc_auc = roc_auc_score(
        y_validation,
        validation_probabilities,
    )

    validation_pr_auc = (
        average_precision_score(
            y_validation,
            validation_probabilities,
        )
    )

    test_roc_auc = roc_auc_score(
        y_test,
        test_probabilities,
    )

    test_pr_auc = (
        average_precision_score(
            y_test,
            test_probabilities,
        )
    )

    print()
    print(
        f"   Validation ROC-AUC: "
        f"{validation_roc_auc:.4f}"
    )

    print(
        f"   Validation PR-AUC:  "
        f"{validation_pr_auc:.4f}"
    )

    print(
        f"   Test ROC-AUC:       "
        f"{test_roc_auc:.4f}"
    )

    print(
        f"   Test PR-AUC:        "
        f"{test_pr_auc:.4f}"
    )

    # --------------------------------------------------------
    # 7. Search validation thresholds
    # --------------------------------------------------------

    print()
    print(
        "7. Searching thresholds using validation only..."
    )

    validation_results = (
        evaluate_validation_thresholds(
            y_validation=y_validation,
            validation_probabilities=validation_probabilities,
        )
    )

    print_validation_results(
        validation_results
    )

    # --------------------------------------------------------
    # 8. Select best threshold
    # --------------------------------------------------------

    best = select_best_threshold(
        validation_results
    )

    best_threshold = float(
        best["threshold"]
    )

    print()
    print("=" * 80)
    print(
        "SELECTED VALIDATION THRESHOLD"
    )
    print("=" * 80)

    print()
    print(
        f"Threshold: "
        f"{best_threshold:.2f}"
    )

    print(
        f"Validation precision: "
        f"{best['precision']:.4f}"
    )

    print(
        f"Validation recall: "
        f"{best['recall']:.4f}"
    )

    print(
        f"Validation F1: "
        f"{best['f1']:.4f}"
    )

    print(
        f"Customers targeted: "
        f"{int(best['targeted_customers']):,}"
    )

    print(
        f"Target rate: "
        f"{best['target_rate']:.2%}"
    )

    # --------------------------------------------------------
    # 9. Lock threshold
    # --------------------------------------------------------

    print()
    print(
        "8. Locking threshold before test evaluation..."
    )

    print(
        f"   Locked threshold: "
        f"{best_threshold:.2f}"
    )

    print(
        "   [PASS] Test data was not used "
        "for threshold selection"
    )

    # --------------------------------------------------------
    # 10. Evaluate test
    # --------------------------------------------------------

    print()
    print(
        "9. Evaluating locked threshold on test..."
    )

    test_metrics = evaluate_locked_threshold(
        y_test=y_test,
        test_probabilities=test_probabilities,
        threshold=best_threshold,
    )

    print()
    print("=" * 80)
    print(
        "FINAL TEST RESULTS — LOCKED THRESHOLD"
    )
    print("=" * 80)

    print()

    print(
        f"ROC-AUC:   "
        f"{test_roc_auc:.4f}"
    )

    print(
        f"PR-AUC:    "
        f"{test_pr_auc:.4f}"
    )

    print(
        f"Threshold: "
        f"{best_threshold:.2f}"
    )

    print(
        f"Precision: "
        f"{test_metrics['precision']:.4f}"
    )

    print(
        f"Recall:    "
        f"{test_metrics['recall']:.4f}"
    )

    print(
        f"F1:        "
        f"{test_metrics['f1']:.4f}"
    )

    print(
        f"Targeted customers: "
        f"{int(test_metrics['targeted_customers']):,}"
    )

    print(
        f"Target rate: "
        f"{test_metrics['target_rate']:.2%}"
    )

    print()

    print(
        "Confusion matrix:"
    )

    print(
        confusion_matrix(
            y_test,
            (
                test_probabilities
                >= best_threshold
            ).astype(int),
        )
    )

    # --------------------------------------------------------
    # 11. Save threshold analysis
    # --------------------------------------------------------

    print()
    print(
        "10. Saving threshold analysis..."
    )

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    validation_results.to_csv(
        RESULTS_PATH,
        index=False,
    )

    print(
        f"   Saved: {RESULTS_PATH}"
    )

    # --------------------------------------------------------
    # 12. Final summary
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print(
        "THRESHOLD OPTIMIZATION COMPLETE"
    )
    print("=" * 80)

    print()
    print(
        f"Selected threshold: "
        f"{best_threshold:.2f}"
    )

    print(
        f"Test ROC-AUC: "
        f"{test_roc_auc:.4f}"
    )

    print(
        f"Test PR-AUC: "
        f"{test_pr_auc:.4f}"
    )

    print(
        f"Test Precision: "
        f"{test_metrics['precision']:.4f}"
    )

    print(
        f"Test Recall: "
        f"{test_metrics['recall']:.4f}"
    )

    print(
        f"Test F1: "
        f"{test_metrics['f1']:.4f}"
    )

    print()
    print(
        "============================================================"
    )


if __name__ == "__main__":
    main()