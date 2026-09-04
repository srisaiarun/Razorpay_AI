from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

MODEL_PATH = (
    PROJECT_ROOT
    / "models"
    / "logistic_calibrated_isotonic.joblib"
)


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
# CONSTANTS
# ============================================================

MINIMUM_INACTIVITY_DAYS = 45
AT_RISK_MULTIPLIER = 1.25


class RecoveryPredictor:
    """
    Production inference wrapper for the calibrated
    recovery-probability model.
    """

    def __init__(
        self,
        model_path: Path = MODEL_PATH,
    ) -> None:

        self.model_path = Path(model_path)

        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Recovery model not found: {self.model_path}"
            )

        self.model = joblib.load(self.model_path)

        if not hasattr(self.model, "predict_proba"):
            raise RuntimeError(
                "Loaded recovery model does not support "
                "predict_proba()."
            )

    # ========================================================
    # FEATURE VALIDATION
    # ========================================================

    @staticmethod
    def _validate_features(
        features: dict[str, Any],
    ) -> pd.DataFrame:

        missing = [
            column
            for column in FEATURE_COLUMNS
            if column not in features
        ]

        if missing:
            raise ValueError(
                "Missing required recovery-model features: "
                + ", ".join(missing)
            )

        row = {
            column: features[column]
            for column in FEATURE_COLUMNS
        }

        dataframe = pd.DataFrame(
            [row],
            columns=FEATURE_COLUMNS,
        )

        dataframe = dataframe.apply(
            pd.to_numeric,
            errors="coerce",
        )

        if dataframe.isnull().all(axis=None):
            raise ValueError(
                "Recovery-model feature vector contains "
                "no usable numeric values."
            )

        return dataframe

    # ========================================================
    # AT-RISK THRESHOLD
    # ========================================================

    @staticmethod
    def calculate_at_risk_threshold(
        median_days_between_orders: float | None,
    ) -> float:

        if (
            median_days_between_orders is None
            or not np.isfinite(
                median_days_between_orders
            )
        ):
            return float(
                MINIMUM_INACTIVITY_DAYS
            )

        threshold = (
            float(median_days_between_orders)
            * AT_RISK_MULTIPLIER
        )

        return float(
            max(
                threshold,
                MINIMUM_INACTIVITY_DAYS,
            )
        )

    # ========================================================
    # PREDICTION
    # ========================================================

    def predict_probability(
        self,
        features: dict[str, Any],
    ) -> float:

        dataframe = self._validate_features(
            features
        )

        probabilities = self.model.predict_proba(
            dataframe
        )

        if (
            probabilities.ndim != 2
            or probabilities.shape[1] < 2
        ):
            raise RuntimeError(
                "Recovery model returned an invalid "
                "probability matrix."
            )

        probability = float(
            probabilities[0, 1]
        )

        if not np.isfinite(probability):
            raise RuntimeError(
                "Recovery model returned a non-finite "
                "recovery probability."
            )

        return float(
            np.clip(
                probability,
                0.0,
                1.0,
            )
        )

    # ========================================================
    # FULL PREDICTION
    # ========================================================

    def predict(
        self,
        features: dict[str, Any],
    ) -> dict[str, Any]:

        probability = self.predict_probability(
            features
        )

        return {
            "recovery_probability": probability,
            "model": self.model_path.name,
            "feature_count": len(FEATURE_COLUMNS),
        }


# ============================================================
# SINGLETON
# ============================================================

recovery_predictor = RecoveryPredictor()