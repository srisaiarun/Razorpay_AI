from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[4]

SELECTED_POLICY_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "selected_decision_policy.csv"
)


@dataclass(frozen=True)
class RecoveryDecision:
    customer_id: int
    snapshot_date: str | None

    recovery_probability: float
    amount_at_risk: float
    expected_recovery_value: float

    priority_score: float
    priority_rank: str

    recovery_risk_band: str
    priority_band: str

    recommended_action: str
    targeted_by_capacity_policy: bool

    decision_reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DecisionEngine:
    """
    Deterministic production decision engine.

    Responsibilities:
        1. Validate ML probability.
        2. Calculate expected recovery value.
        3. Determine recovery risk band.
        4. Determine priority band.
        5. Determine recommended action.
        6. Apply the locked capacity policy.

    This class does NOT:
        - train models
        - modify model probabilities
        - use future outcomes
        - access the test dataset
        - perform database writes
    """

    def __init__(
        self,
        policy_path: Path | str = SELECTED_POLICY_PATH,
    ) -> None:

        self.policy_path = Path(policy_path)

        self.target_percentage = (
            self._load_locked_policy()
        )

    # ---------------------------------------------------------
    # Policy
    # ---------------------------------------------------------

    def _load_locked_policy(self) -> float:
        if not self.policy_path.exists():
            raise FileNotFoundError(
                "Locked decision policy was not found: "
                f"{self.policy_path}"
            )

        policy = pd.read_csv(
            self.policy_path
        )

        required_columns = {
            "policy_name",
            "target_percentage",
            "selection_basis",
            "ranking_metric",
        }

        missing = (
            required_columns
            - set(policy.columns)
        )

        if missing:
            raise ValueError(
                "Decision policy is missing columns: "
                f"{sorted(missing)}"
            )

        if len(policy) != 1:
            raise ValueError(
                "Locked decision policy must contain "
                "exactly one policy row."
            )

        percentage = float(
            policy.iloc[0]["target_percentage"]
        )

        if not 0 < percentage <= 1:
            raise ValueError(
                "target_percentage must be between "
                "0 and 1."
            )

        selection_basis = str(
            policy.iloc[0]["selection_basis"]
        )

        if selection_basis != "validation_only":
            raise ValueError(
                "Production policy must have been "
                "selected using validation data only."
            )

        ranking_metric = str(
            policy.iloc[0]["ranking_metric"]
        )

        if ranking_metric != "expected_recovery_value":
            raise ValueError(
                "Unexpected production ranking metric: "
                f"{ranking_metric}"
            )

        return percentage

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------

    @staticmethod
    def _validate_customer_id(
        customer_id: int,
    ) -> int:

        try:
            customer_id = int(customer_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "customer_id must be an integer."
            ) from exc

        if customer_id <= 0:
            raise ValueError(
                "customer_id must be positive."
            )

        return customer_id

    @staticmethod
    def _validate_probability(
        probability: float,
    ) -> float:

        try:
            probability = float(probability)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "recovery_probability must be numeric."
            ) from exc

        if not 0 <= probability <= 1:
            raise ValueError(
                "recovery_probability must be "
                "between 0 and 1."
            )

        return probability

    @staticmethod
    def _validate_amount(
        amount: float,
        field_name: str,
    ) -> float:

        try:
            amount = float(amount)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"{field_name} must be numeric."
            ) from exc

        if amount < 0:
            raise ValueError(
                f"{field_name} cannot be negative."
            )

        return amount

    # ---------------------------------------------------------
    # Risk
    # ---------------------------------------------------------

    @staticmethod
    def _risk_band(
        probability: float,
    ) -> str:

        if probability >= 0.70:
            return "HIGH"

        if probability >= 0.40:
            return "MEDIUM"

        return "LOW"

    # ---------------------------------------------------------
    # Priority
    # ---------------------------------------------------------

    @staticmethod
    def _priority_band(
        probability: float,
        expected_value: float,
    ) -> str:

        if (
            probability >= 0.70
            and expected_value >= 1000
        ):
            return "P1_HIGH"

        if (
            probability >= 0.55
            and expected_value >= 500
        ):
            return "P2"

        if (
            probability >= 0.40
            and expected_value >= 250
        ):
            return "P3"

        return "P4"

    # ---------------------------------------------------------
    # Action
    # ---------------------------------------------------------

    @staticmethod
    def _recommended_action(
        probability: float,
        expected_value: float,
        priority_band: str,
    ) -> str:

        if priority_band == "P1_HIGH":
            return "HIGH_PRIORITY_RECOVERY"

        if priority_band == "P2":
            return "STANDARD_RECOVERY"

        if priority_band == "P3":
            return "LOW_COST_RECOVERY"

        if (
            probability >= 0.25
            and expected_value >= 100
        ):
            return "MONITOR"

        return "NO_ACTION"

    # ---------------------------------------------------------
    # Score
    # ---------------------------------------------------------

    @staticmethod
    def _priority_score(
        probability: float,
        expected_value: float,
        amount_at_risk: float,
    ) -> float:
        """
        Deterministic score for operational ordering.

        70% expected-value component
        30% recovery-probability component

        Expected value is normalized against amount at risk,
        which effectively represents recovery probability.

        Therefore the score remains bounded between 0 and 100.
        """

        if amount_at_risk <= 0:
            return round(
                probability * 30,
                2,
            )

        value_ratio = (
            expected_value
            / amount_at_risk
        )

        value_ratio = max(
            0.0,
            min(
                1.0,
                value_ratio,
            ),
        )

        score = (
            70 * value_ratio
            + 30 * probability
        )

        return round(
            score,
            2,
        )

    # ---------------------------------------------------------
    # Reason
    # ---------------------------------------------------------

    @staticmethod
    def _decision_reason(
        probability: float,
        expected_value: float,
        amount_at_risk: float,
        risk_band: str,
        priority_band: str,
        action: str,
    ) -> str:

        probability_pct = (
            probability * 100
        )

        if amount_at_risk > 0:
            expected_value_pct = (
                expected_value
                / amount_at_risk
                * 100
            )
        else:
            expected_value_pct = 0.0

        return (
            f"Recovery probability is "
            f"{probability_pct:.1f}% with "
            f"{risk_band} recovery risk. "
            f"Amount at risk is "
            f"£{amount_at_risk:,.2f} and expected "
            f"recovery value is "
            f"£{expected_value:,.2f} "
            f"({expected_value_pct:.1f}% expected recovery). "
            f"Decision: {action} "
            f"under {priority_band} policy."
        )

    # ---------------------------------------------------------
    # Main decision
    # ---------------------------------------------------------

    def decide(
        self,
        *,
        customer_id: int,
        recovery_probability: float,
        amount_at_risk: float,
        snapshot_date: str | None = None,
    ) -> RecoveryDecision:

        customer_id = (
            self._validate_customer_id(
                customer_id
            )
        )

        probability = (
            self._validate_probability(
                recovery_probability
            )
        )

        amount = (
            self._validate_amount(
                amount_at_risk,
                "amount_at_risk",
            )
        )

        expected_value = (
            probability * amount
        )

        expected_value = round(
            expected_value,
            2,
        )

        risk_band = (
            self._risk_band(
                probability
            )
        )

        priority_band = (
            self._priority_band(
                probability,
                expected_value,
            )
        )

        action = (
            self._recommended_action(
                probability,
                expected_value,
                priority_band,
            )
        )

        score = (
            self._priority_score(
                probability,
                expected_value,
                amount,
            )
        )

        targeted = (
            action != "NO_ACTION"
        )

        reason = (
            self._decision_reason(
                probability,
                expected_value,
                amount,
                risk_band,
                priority_band,
                action,
            )
        )

        return RecoveryDecision(
            customer_id=customer_id,
            snapshot_date=snapshot_date,
            recovery_probability=round(
                probability,
                6,
            ),
            amount_at_risk=round(
                amount,
                2,
            ),
            expected_recovery_value=expected_value,
            priority_score=score,
            priority_rank="UNASSIGNED",
            recovery_risk_band=risk_band,
            priority_band=priority_band,
            recommended_action=action,
            targeted_by_capacity_policy=targeted,
            decision_reason=reason,
        )


# -------------------------------------------------------------
# Local test
# -------------------------------------------------------------

def main() -> None:

    print("=" * 80)
    print("RAZORRECOVER AI — DECISION ENGINE TEST")
    print("=" * 80)

    print()
    print("1. Loading locked decision policy...")

    engine = DecisionEngine()

    print(
        f"   Locked targeting policy: "
        f"{engine.target_percentage:.0%}"
    )

    print(
        "   [PASS] Policy loaded"
    )

    # ---------------------------------------------------------
    # Test cases
    # ---------------------------------------------------------

    test_cases = [
        {
            "customer_id": 12409,
            "recovery_probability": 0.7430,
            "amount_at_risk": 3710.74,
            "snapshot_date": "2011-09-01",
        },
        {
            "customer_id": 13081,
            "recovery_probability": 0.8553,
            "amount_at_risk": 1888.80,
            "snapshot_date": "2011-07-01",
        },
        {
            "customer_id": 12357,
            "recovery_probability": 0.4391,
            "amount_at_risk": 6039.99,
            "snapshot_date": "2011-09-01",
        },
        {
            "customer_id": 18052,
            "recovery_probability": 0.1096,
            "amount_at_risk": 10877.18,
            "snapshot_date": "2011-09-01",
        },
    ]

    print()
    print("2. Running decision examples...")

    decisions: list[RecoveryDecision] = []

    for case in test_cases:

        decision = engine.decide(
            **case
        )

        decisions.append(
            decision
        )

        print()
        print(
            f"Customer: "
            f"{decision.customer_id}"
        )

        print(
            f"  Probability: "
            f"{decision.recovery_probability:.4f}"
        )

        print(
            f"  Amount at risk: "
            f"£{decision.amount_at_risk:,.2f}"
        )

        print(
            f"  Expected recovery: "
            f"£{decision.expected_recovery_value:,.2f}"
        )

        print(
            f"  Risk band: "
            f"{decision.recovery_risk_band}"
        )

        print(
            f"  Priority band: "
            f"{decision.priority_band}"
        )

        print(
            f"  Action: "
            f"{decision.recommended_action}"
        )

        print(
            f"  Priority score: "
            f"{decision.priority_score:.2f}"
        )

        print(
            f"  Reason: "
            f"{decision.decision_reason}"
        )

    # ---------------------------------------------------------
    # Validation tests
    # ---------------------------------------------------------

    print()
    print("3. Testing input validation...")

    invalid_cases = [
        {
            "customer_id": 0,
            "recovery_probability": 0.5,
            "amount_at_risk": 100,
        },
        {
            "customer_id": 123,
            "recovery_probability": 1.5,
            "amount_at_risk": 100,
        },
        {
            "customer_id": 123,
            "recovery_probability": 0.5,
            "amount_at_risk": -100,
        },
    ]

    for case in invalid_cases:

        try:
            engine.decide(**case)

        except ValueError:
            continue

        raise AssertionError(
            "Invalid input was accepted: "
            f"{case}"
        )

    print(
        "   [PASS] Invalid inputs rejected"
    )

    # ---------------------------------------------------------
    # Determinism test
    # ---------------------------------------------------------

    print()
    print("4. Testing deterministic decisions...")

    first = engine.decide(
        customer_id=99999,
        recovery_probability=0.65,
        amount_at_risk=2000,
        snapshot_date="2011-09-01",
    )

    second = engine.decide(
        customer_id=99999,
        recovery_probability=0.65,
        amount_at_risk=2000,
        snapshot_date="2011-09-01",
    )

    if first.to_dict() != second.to_dict():
        raise AssertionError(
            "Decision engine is not deterministic."
        )

    print(
        "   [PASS] Identical inputs produce "
        "identical decisions"
    )

    # ---------------------------------------------------------
    # Expected value test
    # ---------------------------------------------------------

    print()
    print("5. Testing expected recovery calculation...")

    expected = engine.decide(
        customer_id=1,
        recovery_probability=0.75,
        amount_at_risk=1000,
    )

    if expected.expected_recovery_value != 750.00:
        raise AssertionError(
            "Expected recovery value calculation failed."
        )

    print(
        "   [PASS] Expected recovery value calculation"
    )

    print()
    print("=" * 80)
    print("DECISION ENGINE TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()