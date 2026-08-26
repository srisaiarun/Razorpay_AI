from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

TRANSACTIONS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "transactions.parquet"
)

CANCELLATIONS_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "cancellations.parquet"
)

QUALITY_REPORT_PATH = (
    PROJECT_ROOT
    / "data"
    / "reports"
    / "data_quality_report.csv"
)


def validate_transactions() -> None:
    print("=" * 60)
    print("VALIDATING PROCESSED DATA")
    print("=" * 60)

    transactions = pd.read_parquet(
        TRANSACTIONS_PATH,
        engine="pyarrow",
    )

    cancellations = pd.read_parquet(
        CANCELLATIONS_PATH,
        engine="pyarrow",
    )

    quality_report = pd.read_csv(
        QUALITY_REPORT_PATH
    )

    print()
    print("Transactions:")
    print(f"  Rows: {len(transactions):,}")
    print(f"  Columns: {len(transactions.columns)}")

    print()
    print("Transaction schema:")
    print(transactions.dtypes)

    print()
    print("Cancellations:")
    print(f"  Rows: {len(cancellations):,}")
    print(f"  Columns: {len(cancellations.columns)}")

    print()
    print("Validation checks:")

    assert len(transactions) > 0
    print("  [PASS] Transactions are not empty")

    assert len(cancellations) > 0
    print("  [PASS] Cancellations are not empty")

    assert transactions["customer_id"].notna().all()
    print("  [PASS] No missing customer IDs")

    assert (transactions["quantity"] > 0).all()
    print("  [PASS] All transaction quantities are positive")

    assert (transactions["unit_price"] > 0).all()
    print("  [PASS] All transaction prices are positive")

    assert (
        transactions["transaction_amount"] > 0
    ).all()
    print("  [PASS] All transaction amounts are positive")

    assert (
        transactions["invoice_date"].notna().all()
    )
    print("  [PASS] All transaction dates are valid")

    assert transactions["invoice"].notna().all()
    print("  [PASS] All invoices are present")

    assert transactions["stock_code"].notna().all()
    print("  [PASS] All stock codes are present")

    assert (
        transactions["transaction_amount"]
        .equals(
            transactions["quantity"]
            * transactions["unit_price"]
        )
    )
    print("  [PASS] Transaction amounts are mathematically consistent")

    assert (
        cancellations["transaction_amount"] >= 0
    ).all()
    print("  [PASS] Cancellation amounts are non-negative")

    assert QUALITY_REPORT_PATH.exists()
    print("  [PASS] Quality report exists")

    assert len(quality_report) > 0
    print("  [PASS] Quality report contains metrics")

    print()
    print("=" * 60)
    print("ALL VALIDATION CHECKS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    validate_transactions()