from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_DIR = PROJECT_ROOT / "models"

TRAIN_PATH = DATA_DIR / "ml_train.parquet"
VALIDATION_PATH = DATA_DIR / "ml_validation.parquet"
TEST_PATH = DATA_DIR / "ml_test.parquet"

SIGMOID_MODEL_PATH = (
    MODEL_DIR / "logistic_calibrated_sigmoid.joblib"
)

ISOTONIC_MODEL_PATH = (
    MODEL_DIR / "logistic_calibrated_isotonic.joblib"
)

RESULTS_PATH = (
    DATA_DIR / "calibration_model_comparison.csv"
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
# LOG TRANSFORM FEATURES
# ============================================================

LOG_FEATURES = [
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
]


# ============================================================
# DATA LOADING
# ============================================================

def load_dataset(path: Path) -> pd.DataFrame:

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
            f"{name} is missing target '{TARGET}'."
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
            f"{name} contains invalid "
            f"target values: {target_values}"
        )

    print(
        f"   [PASS] {name} validation"
    )


# ============================================================
# FEATURE PREPARATION
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

    # --------------------------------------------------------
    # Important:
    #
    # These features can legitimately be NaN for customers
    # with only one observed purchase:
    #
    # average_days_between_orders
    # median_days_between_orders
    #
    # Therefore we DO NOT drop rows.
    #
    # The pipeline handles missing values.
    # --------------------------------------------------------

    return X, y


# ============================================================
# PREPROCESSOR
# ============================================================

def build_preprocessor() -> ColumnTransformer:

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                ),
            ),
            (
                "scaler",
                StandardScaler(),
            ),
        ]
    )

    return ColumnTransformer(
        transformers=[
            (
                "numeric",
                numeric_pipeline,
                FEATURE_COLUMNS,
            ),
        ],
        remainder="drop",
    )


# ============================================================
# BASE LOGISTIC MODEL
# ============================================================

def build_base_logistic() -> Pipeline:

    preprocessor = build_preprocessor()

    classifier = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        random_state=42,
    )

    return Pipeline(
        steps=[
            (
                "preprocessor",
                preprocessor,
            ),
            (
                "classifier",
                classifier,
            ),
        ]
    )


# ============================================================
# CALIBRATED MODEL
# ============================================================

def build_calibrated_model(
    method: str,
) -> CalibratedClassifierCV:

    base_model = build_base_logistic()

    return CalibratedClassifierCV(
        estimator=base_model,
        method=method,
        cv=5,
        n_jobs=-1,
    )


# ============================================================
# ECE
# ============================================================

def calculate_ece(
    y_true: pd.Series,
    probabilities: np.ndarray,
    n_bins: int = 10,
) -> float:

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
            observed_rate=(
                "actual",
                "mean",
            ),
            count=(
                "actual",
                "count",
            ),
        )
    )

    grouped = grouped[
        grouped["count"] > 0
    ]

    total = grouped[
        "count"
    ].sum()

    if total == 0:
        return 0.0

    weighted_error = (
        (
            grouped[
                "predicted_probability"
            ]
            - grouped[
                "observed_rate"
            ]
        ).abs()
        * grouped["count"]
    ).sum()

    return float(
        weighted_error / total
    )


# ============================================================
# METRICS
# ============================================================

def evaluate_probabilities(
    y_true: pd.Series,
    probabilities: np.ndarray,
) -> dict[str, float]:

    probabilities = np.asarray(
        probabilities,
        dtype=float,
    )

    if not np.isfinite(
        probabilities
    ).all():

        raise ValueError(
            "Probability output contains "
            "NaN or infinite values."
        )

    probabilities = np.clip(
        probabilities,
        1e-7,
        1 - 1e-7,
    )

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
        "ece": calculate_ece(
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
        "CALIBRATED LOGISTIC REGRESSION"
    )
    print("=" * 90)

    # --------------------------------------------------------
    # 1. Load data
    # --------------------------------------------------------

    print()
    print(
        "1. Loading temporal datasets..."
    )

    train = load_dataset(
        TRAIN_PATH
    )

    validation = load_dataset(
        VALIDATION_PATH
    )

    test = load_dataset(
        TEST_PATH
    )

    print(
        f"   Train:      {len(train):,} rows"
    )

    print(
        f"   Validation: {len(validation):,} rows"
    )

    print(
        f"   Test:       {len(test):,} rows"
    )

    # --------------------------------------------------------
    # 2. Validate
    # --------------------------------------------------------

    print()
    print(
        "2. Validating datasets..."
    )

    validate_dataset(
        train,
        "Train",
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
    # 3. Prepare data
    # --------------------------------------------------------

    print()
    print(
        "3. Preparing feature matrices..."
    )

    X_train, y_train = prepare_features(
        train
    )

    X_validation, y_validation = (
        prepare_features(validation)
    )

    X_test, y_test = prepare_features(
        test
    )

    print(
        f"   X_train:      {X_train.shape}"
    )

    print(
        f"   X_validation: {X_validation.shape}"
    )

    print(
        f"   X_test:       {X_test.shape}"
    )

    # --------------------------------------------------------
    # 4. Check missing values
    # --------------------------------------------------------

    print()
    print(
        "4. Checking feature missingness..."
    )

    train_missing = (
        X_train.isna()
        .sum()
        .sum()
    )

    validation_missing = (
        X_validation.isna()
        .sum()
        .sum()
    )

    test_missing = (
        X_test.isna()
        .sum()
        .sum()
    )

    print(
        f"   Train missing values: "
        f"{train_missing:,}"
    )

    print(
        f"   Validation missing values: "
        f"{validation_missing:,}"
    )

    print(
        f"   Test missing values: "
        f"{test_missing:,}"
    )

    print(
        "   [PASS] Missing values will be "
        "handled by the training pipeline"
    )

    # --------------------------------------------------------
    # 5. Train calibrated models
    # --------------------------------------------------------

    models = {
        "sigmoid": build_calibrated_model(
            "sigmoid"
        ),
        "isotonic": build_calibrated_model(
            "isotonic"
        ),
    }

    results = []

    for index, (
        name,
        model,
    ) in enumerate(
        models.items(),
        start=1,
    ):

        print()
        print(
            f"5.{index}. Training "
            f"{name} calibration..."
        )

        model.fit(
            X_train,
            y_train,
        )

        print(
            f"   [PASS] {name} model trained"
        )

        # ----------------------------------------------------
        # Validation
        # ----------------------------------------------------

        validation_probabilities = (
            model.predict_proba(
                X_validation
            )[:, 1]
        )

        validation_metrics = (
            evaluate_probabilities(
                y_validation,
                validation_probabilities,
            )
        )

        print()
        print(
            f"   {name.upper()} VALIDATION"
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

        print(
            f"   ECE:         "
            f"{validation_metrics['ece']:.4f}"
        )

        results.append(
            {
                "model": name,
                "split": "validation",
                **validation_metrics,
            }
        )

    # --------------------------------------------------------
    # 6. Select calibration method
    # --------------------------------------------------------

    print()
    print("=" * 90)
    print(
        "CALIBRATION MODEL SELECTION"
    )
    print("=" * 90)

    validation_results = pd.DataFrame(
        results
    )

    # Primary:
    # lower Brier score.
    #
    # Secondary:
    # lower ECE.
    #
    # Tertiary:
    # lower Log Loss.

    validation_results = (
        validation_results.sort_values(
            [
                "brier_score",
                "ece",
                "log_loss",
            ],
            ascending=True,
        )
    )

    winner = (
        validation_results
        .iloc[0]
    )

    winner_name = winner[
        "model"
    ]

    print()
    print(
        "Selection uses validation only."
    )

    print()
    print(
        validation_results.to_string(
            index=False,
            formatters={
                "roc_auc":
                    "{:.4f}".format,
                "pr_auc":
                    "{:.4f}".format,
                "brier_score":
                    "{:.4f}".format,
                "log_loss":
                    "{:.4f}".format,
                "ece":
                    "{:.4f}".format,
            },
        )
    )

    print()
    print(
        f"Selected calibration: "
        f"{winner_name}"
    )

    print(
        f"Validation Brier Score: "
        f"{winner['brier_score']:.4f}"
    )

    print(
        f"Validation ECE: "
        f"{winner['ece']:.4f}"
    )

    print(
        f"Validation Log Loss: "
        f"{winner['log_loss']:.4f}"
    )

    print()
    print(
        "[PASS] Calibration method locked "
        "using validation data only."
    )

    # --------------------------------------------------------
    # 7. Save selected model
    # --------------------------------------------------------

    selected_model = models[
        winner_name
    ]

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if winner_name == "sigmoid":

        selected_path = (
            SIGMOID_MODEL_PATH
        )

    else:

        selected_path = (
            ISOTONIC_MODEL_PATH
        )

    joblib.dump(
        selected_model,
        selected_path,
    )

    print()
    print(
        "7. Saved selected calibrated model:"
    )

    print(
        f"   {selected_path}"
    )

    # --------------------------------------------------------
    # 8. Evaluate locked model on TEST
    # --------------------------------------------------------

    print()
    print(
        "8. Evaluating locked model on "
        "temporal test set..."
    )

    test_probabilities = (
        selected_model.predict_proba(
            X_test
        )[:, 1]
    )

    test_metrics = (
        evaluate_probabilities(
            y_test,
            test_probabilities,
        )
    )

    results.append(
        {
            "model": winner_name,
            "split": "test",
            **test_metrics,
        }
    )

    print()
    print("=" * 90)
    print(
        "FINAL TEST RESULTS — LOCKED CALIBRATED MODEL"
    )
    print("=" * 90)

    print()
    print(
        f"Model:       {winner_name}"
    )

    print(
        f"ROC-AUC:     "
        f"{test_metrics['roc_auc']:.4f}"
    )

    print(
        f"PR-AUC:      "
        f"{test_metrics['pr_auc']:.4f}"
    )

    print(
        f"Brier Score: "
        f"{test_metrics['brier_score']:.4f}"
    )

    print(
        f"Log Loss:    "
        f"{test_metrics['log_loss']:.4f}"
    )

    print(
        f"ECE:         "
        f"{test_metrics['ece']:.4f}"
    )

    # --------------------------------------------------------
    # 9. Compare against raw baseline
    # --------------------------------------------------------

    print()
    print(
        "9. Comparing against raw Logistic "
        "Regression baseline..."
    )

    raw_model_path = (
        MODEL_DIR
        / "logistic_baseline.joblib"
    )

    if raw_model_path.exists():

        raw_model = joblib.load(
            raw_model_path
        )

        raw_probabilities = (
            raw_model.predict_proba(
                X_test
            )[:, 1]
        )

        raw_metrics = (
            evaluate_probabilities(
                y_test,
                raw_probabilities,
            )
        )

        comparison = pd.DataFrame(
            [
                {
                    "model":
                        "raw_logistic",
                    "split":
                        "test",
                    **raw_metrics,
                },
                {
                    "model":
                        f"calibrated_{winner_name}",
                    "split":
                        "test",
                    **test_metrics,
                },
            ]
        )

        print()
        print(
            comparison.to_string(
                index=False,
                formatters={
                    "roc_auc":
                        "{:.4f}".format,
                    "pr_auc":
                        "{:.4f}".format,
                    "brier_score":
                        "{:.4f}".format,
                    "log_loss":
                        "{:.4f}".format,
                    "ece":
                        "{:.4f}".format,
                },
            )
        )

    else:

        print(
            "   Raw baseline not found; "
            "comparison skipped."
        )

    # --------------------------------------------------------
    # 10. Save results
    # --------------------------------------------------------

    results_df = pd.DataFrame(
        results
    )

    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    results_df.to_csv(
        RESULTS_PATH,
        index=False,
    )

    print()
    print(
        "10. Saved calibration comparison:"
    )

    print(
        f"   {RESULTS_PATH}"
    )

    # --------------------------------------------------------
    # COMPLETE
    # --------------------------------------------------------

    print()
    print("=" * 90)
    print(
        "CALIBRATED MODEL EVALUATION COMPLETE"
    )
    print("=" * 90)


if __name__ == "__main__":
    main()