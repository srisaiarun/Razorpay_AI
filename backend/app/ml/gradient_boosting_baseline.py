from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_DIR = PROJECT_ROOT / "models"

TRAIN_PATH = DATA_DIR / "ml_train.parquet"
VALIDATION_PATH = DATA_DIR / "ml_validation.parquet"
TEST_PATH = DATA_DIR / "ml_test.parquet"

MODEL_PATH = MODEL_DIR / "gradient_boosting_baseline.joblib"


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


def load_split(path: Path) -> pd.DataFrame:
    """Load one ML dataset."""

    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found:\n{path}"
        )

    return pd.read_parquet(
        path,
        engine="pyarrow",
    )


# ============================================================
# PREPARE FEATURES
# ============================================================


def prepare_features(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series]:
    """Select approved features and target."""

    missing_features = [
        column
        for column in FEATURE_COLUMNS
        if column not in df.columns
    ]

    if missing_features:
        raise ValueError(
            "Missing required features:\n"
            + "\n".join(
                f"  - {column}"
                for column in missing_features
            )
        )

    if TARGET not in df.columns:
        raise ValueError(
            f"Target column '{TARGET}' is missing."
        )

    X = df[
        FEATURE_COLUMNS
    ].copy()

    y = df[
        TARGET
    ].astype(int)

    return X, y


# ============================================================
# LEAKAGE CHECK
# ============================================================


def validate_feature_selection() -> None:
    """Prevent target, future, and identifier leakage."""

    forbidden_columns = {
        "customer_id",
        "snapshot_date",
        "first_purchase_date",
        "last_purchase_date",
        "future_purchase_count",
        "future_spend",
        "recovered",
        "at_risk",
    }

    leakage_columns = (
        set(FEATURE_COLUMNS)
        & forbidden_columns
    )

    if leakage_columns:
        raise AssertionError(
            "Potential leakage detected:\n"
            + "\n".join(
                f"  - {column}"
                for column in sorted(
                    leakage_columns
                )
            )
        )

    print(
        "   [PASS] No target, future, "
        "or identifier leakage"
    )


# ============================================================
# BUILD MODEL
# ============================================================


def build_pipeline() -> Pipeline:
    """
    Build HistGradientBoosting pipeline.

    Median imputation is used before the classifier so the
    feature matrix has no missing values.
    """

    imputer = SimpleImputer(
        strategy="median"
    )

    classifier = HistGradientBoostingClassifier(
        learning_rate=0.05,
        max_iter=300,
        max_leaf_nodes=15,
        min_samples_leaf=30,
        l2_regularization=1.0,
        early_stopping=True,
        validation_fraction=0.10,
        n_iter_no_change=30,
        random_state=42,
    )

    return Pipeline(
        steps=[
            (
                "imputer",
                imputer,
            ),
            (
                "classifier",
                classifier,
            ),
        ]
    )


# ============================================================
# EVALUATION
# ============================================================


def evaluate(
    name: str,
    model: Pipeline,
    X: pd.DataFrame,
    y: pd.Series,
) -> dict[str, float]:

    probabilities = model.predict_proba(
        X
    )[:, 1]

    predictions = (
        probabilities >= 0.5
    ).astype(int)

    roc_auc = roc_auc_score(
        y,
        probabilities,
    )

    pr_auc = average_precision_score(
        y,
        probabilities,
    )

    precision = precision_score(
        y,
        predictions,
        zero_division=0,
    )

    recall = recall_score(
        y,
        predictions,
        zero_division=0,
    )

    f1 = f1_score(
        y,
        predictions,
        zero_division=0,
    )

    print()
    print("=" * 60)
    print(name)
    print("=" * 60)

    print()
    print(
        f"ROC-AUC:   {roc_auc:.4f}"
    )

    print(
        f"PR-AUC:    {pr_auc:.4f}"
    )

    print(
        f"Precision: {precision:.4f}"
    )

    print(
        f"Recall:    {recall:.4f}"
    )

    print(
        f"F1:        {f1:.4f}"
    )

    print()
    print("Confusion matrix:")

    print(
        confusion_matrix(
            y,
            predictions,
        )
    )

    print()
    print("Classification report:")

    print(
        classification_report(
            y,
            predictions,
            digits=4,
            zero_division=0,
        )
    )

    return {
        "roc_auc": roc_auc,
        "pr_auc": pr_auc,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


# ============================================================
# FEATURE IMPORTANCE
# ============================================================


def print_feature_importance(
    model: Pipeline,
) -> None:
    """
    Display permutation-style model importance using
    the built-in feature_importances_ attribute if available.

    HistGradientBoostingClassifier does not expose
    feature_importances_, so we use permutation importance
    on the validation set.
    """

    from sklearn.inspection import permutation_importance

    classifier = model.named_steps[
        "classifier"
    ]

    # Retrieve the transformed validation data through
    # the fitted preprocessing step.
    #
    # This function is called separately from main with
    # validation data, so this helper is intentionally
    # handled there instead.
    return None


def calculate_permutation_importance(
    model: Pipeline,
    X: pd.DataFrame,
    y: pd.Series,
) -> None:
    """Calculate and print validation permutation importance."""

    from sklearn.inspection import permutation_importance

    result = permutation_importance(
        model,
        X,
        y,
        scoring="roc_auc",
        n_repeats=5,
        random_state=42,
        n_jobs=-1,
    )

    importance_df = pd.DataFrame(
        {
            "feature": FEATURE_COLUMNS,
            "importance_mean": result.importances_mean,
            "importance_std": result.importances_std,
        }
    ).sort_values(
        "importance_mean",
        ascending=False,
    )

    print()
    print("=" * 60)
    print(
        "VALIDATION PERMUTATION IMPORTANCE"
    )
    print("=" * 60)

    print()

    for _, row in importance_df.iterrows():
        print(
            f"{row['feature']:<35} "
            f"{row['importance_mean']:.6f} "
            f"+/- {row['importance_std']:.6f}"
        )


# ============================================================
# MAIN
# ============================================================


def main() -> None:

    print("=" * 60)
    print(
        "RAZORRECOVER AI — "
        "HISTOGRAM GRADIENT BOOSTING BASELINE"
    )
    print("=" * 60)

    # --------------------------------------------------------
    # 1. Validate feature configuration
    # --------------------------------------------------------

    print()
    print(
        "1. Validating feature configuration..."
    )

    validate_feature_selection()

    print(
        f"   Model features: "
        f"{len(FEATURE_COLUMNS)}"
    )

    # --------------------------------------------------------
    # 2. Load datasets
    # --------------------------------------------------------

    print()
    print("2. Loading datasets...")

    train = load_split(
        TRAIN_PATH
    )

    validation = load_split(
        VALIDATION_PATH
    )

    test = load_split(
        TEST_PATH
    )

    print(
        f"   Train:      "
        f"{len(train):,} rows"
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
    # 3. Prepare features
    # --------------------------------------------------------

    print()
    print(
        "3. Preparing feature matrices..."
    )

    X_train, y_train = prepare_features(
        train
    )

    X_validation, y_validation = (
        prepare_features(
            validation
        )
    )

    X_test, y_test = prepare_features(
        test
    )

    print(
        f"   X_train:      "
        f"{X_train.shape}"
    )

    print(
        f"   X_validation: "
        f"{X_validation.shape}"
    )

    print(
        f"   X_test:       "
        f"{X_test.shape}"
    )

    # --------------------------------------------------------
    # 4. Validate target
    # --------------------------------------------------------

    print()
    print("4. Validating target...")

    for name, target in [
        ("train", y_train),
        ("validation", y_validation),
        ("test", y_test),
    ]:

        unique_values = set(
            target.unique()
        )

        if not unique_values.issubset(
            {0, 1}
        ):
            raise ValueError(
                f"{name} contains invalid "
                f"target values: "
                f"{unique_values}"
            )

        print(
            f"   {name}: "
            f"{target.sum():,} positive / "
            f"{len(target):,} total "
            f"({target.mean():.2%})"
        )

    print(
        "   [PASS] Target is binary"
    )

    # --------------------------------------------------------
    # 5. Build model
    # --------------------------------------------------------

    print()
    print(
        "5. Building Gradient Boosting pipeline..."
    )

    model = build_pipeline()

    print(
        "   Pipeline created."
    )

    # --------------------------------------------------------
    # 6. Train
    # --------------------------------------------------------

    print()
    print(
        "6. Training Gradient Boosting..."
    )

    model.fit(
        X_train,
        y_train,
    )

    classifier = model.named_steps[
        "classifier"
    ]

    print(
        "   [PASS] Training completed"
    )

    print(
        f"   Boosting iterations used: "
        f"{classifier.n_iter_}"
    )

    # --------------------------------------------------------
    # 7. Validation
    # --------------------------------------------------------

    print()
    print(
        "7. Evaluating validation set..."
    )

    validation_metrics = evaluate(
        name="VALIDATION RESULTS",
        model=model,
        X=X_validation,
        y=y_validation,
    )

    # --------------------------------------------------------
    # 8. Test
    # --------------------------------------------------------

    print()
    print(
        "8. Evaluating test set..."
    )

    test_metrics = evaluate(
        name="TEST RESULTS",
        model=model,
        X=X_test,
        y=y_test,
    )

    # --------------------------------------------------------
    # 9. Feature importance
    # --------------------------------------------------------

    print()
    print(
        "9. Calculating feature importance..."
    )

    calculate_permutation_importance(
        model=model,
        X=X_validation,
        y=y_validation,
    )

    # --------------------------------------------------------
    # 10. Save model
    # --------------------------------------------------------

    print()
    print(
        "10. Saving trained model..."
    )

    MODEL_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    joblib.dump(
        model,
        MODEL_PATH,
    )

    print(
        f"   Saved: {MODEL_PATH}"
    )

    # --------------------------------------------------------
    # 11. Final summary
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print(
        "GRADIENT BOOSTING BASELINE COMPLETE"
    )
    print("=" * 60)

    print()
    print("Validation:")

    print(
        f"  ROC-AUC:   "
        f"{validation_metrics['roc_auc']:.4f}"
    )

    print(
        f"  PR-AUC:    "
        f"{validation_metrics['pr_auc']:.4f}"
    )

    print(
        f"  Precision: "
        f"{validation_metrics['precision']:.4f}"
    )

    print(
        f"  Recall:    "
        f"{validation_metrics['recall']:.4f}"
    )

    print(
        f"  F1:        "
        f"{validation_metrics['f1']:.4f}"
    )

    print()
    print("Test:")

    print(
        f"  ROC-AUC:   "
        f"{test_metrics['roc_auc']:.4f}"
    )

    print(
        f"  PR-AUC:    "
        f"{test_metrics['pr_auc']:.4f}"
    )

    print(
        f"  Precision: "
        f"{test_metrics['precision']:.4f}"
    )

    print(
        f"  Recall:    "
        f"{test_metrics['recall']:.4f}"
    )

    print(
        f"  F1:        "
        f"{test_metrics['f1']:.4f}"
    )

    print()
    print(
        f"Model artifact: {MODEL_PATH}"
    )

    print()
    print("=" * 60)


if __name__ == "__main__":
    main()