from __future__ import annotations

from pathlib import Path

import pandas as pd


# ============================================================
# Project paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[3]

RAW_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "online_retail_II.xlsx"
)

PROCESSED_DIR = (
    PROJECT_ROOT
    / "data"
    / "processed"
)

REPORTS_DIR = (
    PROJECT_ROOT
    / "data"
    / "reports"
)

TRANSACTIONS_PATH = (
    PROCESSED_DIR
    / "transactions.parquet"
)

CANCELLATIONS_PATH = (
    PROCESSED_DIR
    / "cancellations.parquet"
)

QUALITY_REPORT_PATH = (
    REPORTS_DIR
    / "data_quality_report.csv"
)


# ============================================================
# Expected source columns
# ============================================================

EXPECTED_COLUMNS = [
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "Price",
    "Customer ID",
    "Country",
]


# ============================================================
# Loading
# ============================================================

def load_raw_dataset() -> pd.DataFrame:
    """
    Load all sheets from the Online Retail II workbook
    and combine them into a single DataFrame.
    """

    if not RAW_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found at: {RAW_PATH}"
        )

    sheets = pd.read_excel(
        RAW_PATH,
        sheet_name=None,
        engine="openpyxl",
    )

    if not sheets:
        raise ValueError(
            "No worksheets were found in the dataset."
        )

    frames: list[pd.DataFrame] = []

    for sheet_name, frame in sheets.items():

        if frame.empty:
            continue

        frame = frame.copy()

        # Preserve the source sheet for traceability.
        frame["source_sheet"] = str(sheet_name)

        frames.append(frame)

    if not frames:
        raise ValueError(
            "All worksheets in the dataset are empty."
        )

    dataset = pd.concat(
        frames,
        ignore_index=True,
    )

    return dataset


# ============================================================
# Schema validation
# ============================================================

def validate_source_schema(
    dataset: pd.DataFrame,
) -> None:
    """
    Verify that the published dataset still has the
    columns our pipeline expects.
    """

    missing_columns = [
        column
        for column in EXPECTED_COLUMNS
        if column not in dataset.columns
    ]

    if missing_columns:
        raise ValueError(
            "Dataset schema validation failed. "
            f"Missing columns: {missing_columns}"
        )


# ============================================================
# Column standardization
# ============================================================

def standardize_columns(
    dataset: pd.DataFrame,
) -> pd.DataFrame:
    """
    Rename source columns into consistent internal names.
    """

    df = dataset.copy()

    df = df.rename(
        columns={
            "Invoice": "invoice",
            "StockCode": "stock_code",
            "Description": "description",
            "Quantity": "quantity",
            "InvoiceDate": "invoice_date",
            "Price": "unit_price",
            "Customer ID": "customer_id",
            "Country": "country",
        }
    )

    return df


# ============================================================
# Type normalization
# ============================================================

def normalize_types(
    dataset: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normalize every important field into an explicit type.

    Identifiers and categorical fields are strings.
    Measurements are numeric.
    Dates are datetime.
    """

    df = dataset.copy()

    # --------------------------------------------------------
    # String / identifier fields
    # --------------------------------------------------------

    string_columns = [
        "invoice",
        "stock_code",
        "description",
        "country",
        "source_sheet",
    ]

    for column in string_columns:

        if column in df.columns:
            df[column] = (
                df[column]
                .astype("string")
                .str.strip()
            )

    # --------------------------------------------------------
    # Numeric fields
    # --------------------------------------------------------

    df["quantity"] = pd.to_numeric(
        df["quantity"],
        errors="coerce",
    )

    df["unit_price"] = pd.to_numeric(
        df["unit_price"],
        errors="coerce",
    )

    df["customer_id"] = pd.to_numeric(
        df["customer_id"],
        errors="coerce",
    )

    # --------------------------------------------------------
    # Datetime
    # --------------------------------------------------------

    df["invoice_date"] = pd.to_datetime(
        df["invoice_date"],
        errors="coerce",
    )

    return df


# ============================================================
# Cancellation identification
# ============================================================

def identify_cancellations(
    dataset: pd.DataFrame,
) -> pd.Series:
    """
    Identify cancellation / return records.

    The Online Retail II dataset uses:
      - negative quantities
      - invoice numbers beginning with 'C'

    We preserve these records separately rather than
    silently deleting them.
    """

    invoice_is_cancellation = (
        dataset["invoice"]
        .fillna("")
        .str.upper()
        .str.startswith("C")
    )

    negative_quantity = (
        dataset["quantity"] < 0
    )

    return (
        invoice_is_cancellation
        | negative_quantity
    )


# ============================================================
# Data cleaning
# ============================================================

def clean_dataset(
    dataset: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Clean the raw dataset.

    Returns:
        transactions
        cancellations
        quality_report
    """

    df = dataset.copy()

    original_row_count = len(df)

    # --------------------------------------------------------
    # Schema
    # --------------------------------------------------------

    validate_source_schema(df)

    # --------------------------------------------------------
    # Standardize names
    # --------------------------------------------------------

    df = standardize_columns(df)

    # --------------------------------------------------------
    # Normalize data types
    # --------------------------------------------------------

    df = normalize_types(df)

    # --------------------------------------------------------
    # Track invalid rows before removing them
    # --------------------------------------------------------

    invalid_invoice = df["invoice"].isna()

    invalid_date = df["invoice_date"].isna()

    invalid_quantity = df["quantity"].isna()

    invalid_price = df["unit_price"].isna()

    invalid_core_row = (
        invalid_invoice
        | invalid_date
        | invalid_quantity
        | invalid_price
    )

    invalid_core_rows = int(
        invalid_core_row.sum()
    )

    # --------------------------------------------------------
    # Remove rows that cannot represent a transaction
    # --------------------------------------------------------

    df = df.loc[
        ~invalid_core_row
    ].copy()

    # --------------------------------------------------------
    # Identify cancellations BEFORE filtering purchases
    # --------------------------------------------------------

    cancellation_mask = identify_cancellations(df)

    cancellations = df.loc[
        cancellation_mask
    ].copy()

    # --------------------------------------------------------
    # Calculate cancellation amount
    # --------------------------------------------------------

    cancellations["transaction_amount"] = (
        cancellations["quantity"]
        .abs()
        * cancellations["unit_price"]
        .abs()
    )

    # --------------------------------------------------------
    # Identify valid purchase transactions
    # --------------------------------------------------------

    transactions = df.loc[
        ~cancellation_mask
    ].copy()

    # Only positive quantity and positive price represent
    # normal purchases for our customer-behavior model.
    transactions = transactions.loc[
        (transactions["quantity"] > 0)
        & (transactions["unit_price"] > 0)
    ].copy()

    # --------------------------------------------------------
    # Customer-level ML requires a Customer ID
    # --------------------------------------------------------

    missing_customer_id_rows = int(
        transactions["customer_id"]
        .isna()
        .sum()
    )

    transactions = transactions.loc[
        transactions["customer_id"].notna()
    ].copy()

    # --------------------------------------------------------
    # Transaction amount
    # --------------------------------------------------------

    transactions["transaction_amount"] = (
        transactions["quantity"]
        * transactions["unit_price"]
    )

    # --------------------------------------------------------
    # Remove exact duplicate purchase rows
    # --------------------------------------------------------

    duplicate_transaction_rows = int(
        transactions.duplicated().sum()
    )

    transactions = transactions.drop_duplicates(
        keep="first"
    ).copy()

    # --------------------------------------------------------
    # Remove exact duplicate cancellation rows
    # --------------------------------------------------------

    duplicate_cancellation_rows = int(
        cancellations.duplicated().sum()
    )

    cancellations = cancellations.drop_duplicates(
        keep="first"
    ).copy()

    # --------------------------------------------------------
    # Final column ordering
    # --------------------------------------------------------

    preferred_columns = [
        "invoice",
        "stock_code",
        "description",
        "quantity",
        "invoice_date",
        "unit_price",
        "customer_id",
        "country",
        "source_sheet",
        "transaction_amount",
    ]

    transactions = transactions[
        [
            column
            for column in preferred_columns
            if column in transactions.columns
        ]
    ]

    cancellations = cancellations[
        [
            column
            for column in preferred_columns
            if column in cancellations.columns
        ]
    ]

    # --------------------------------------------------------
    # Build quality report
    # --------------------------------------------------------

    quality_records = [
        {
            "metric": "raw_rows",
            "value": original_row_count,
        },
        {
            "metric": "invalid_core_rows_removed",
            "value": invalid_core_rows,
        },
        {
            "metric": "clean_transaction_rows",
            "value": len(transactions),
        },
        {
            "metric": "cancellation_rows",
            "value": len(cancellations),
        },
        {
            "metric": "missing_customer_id_rows_excluded",
            "value": missing_customer_id_rows,
        },
        {
            "metric": "duplicate_transaction_rows_removed",
            "value": duplicate_transaction_rows,
        },
        {
            "metric": "duplicate_cancellation_rows_removed",
            "value": duplicate_cancellation_rows,
        },
        {
            "metric": "unique_customers",
            "value": transactions["customer_id"].nunique(),
        },
        {
            "metric": "unique_invoices",
            "value": transactions["invoice"].nunique(),
        },
        {
            "metric": "unique_products",
            "value": transactions["stock_code"].nunique(),
        },
        {
            "metric": "unique_countries",
            "value": transactions["country"].nunique(),
        },
        {
            "metric": "total_transaction_value",
            "value": float(
                transactions[
                    "transaction_amount"
                ].sum()
            ),
        },
        {
            "metric": "total_cancellation_value",
            "value": float(
                cancellations[
                    "transaction_amount"
                ].sum()
            ),
        },
    ]

    quality_report = pd.DataFrame(
        quality_records
    )

    return (
        transactions,
        cancellations,
        quality_report,
    )


# ============================================================
# Save processed data
# ============================================================

def save_processed_data(
    transactions: pd.DataFrame,
    cancellations: pd.DataFrame,
    quality_report: pd.DataFrame,
) -> None:
    """
    Save processed datasets and the quality report.
    """

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    REPORTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Explicitly use the PyArrow engine.
    transactions.to_parquet(
        TRANSACTIONS_PATH,
        index=False,
        engine="pyarrow",
    )

    cancellations.to_parquet(
        CANCELLATIONS_PATH,
        index=False,
        engine="pyarrow",
    )

    quality_report.to_csv(
        QUALITY_REPORT_PATH,
        index=False,
    )


# ============================================================
# Main pipeline
# ============================================================

def main() -> None:

    print("=" * 60)
    print("Online Retail II - Data Cleaning Pipeline")
    print("=" * 60)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    print()
    print("1. Loading raw dataset...")

    raw = load_raw_dataset()

    print(
        f"   Raw rows: {len(raw):,}"
    )

    # --------------------------------------------------------
    # Clean
    # --------------------------------------------------------

    print()
    print("2. Validating and cleaning...")

    (
        transactions,
        cancellations,
        quality_report,
    ) = clean_dataset(raw)

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    print()
    print("3. Saving processed datasets...")

    save_processed_data(
        transactions,
        cancellations,
        quality_report,
    )

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print()
    print("=" * 60)
    print("CLEANING COMPLETE")
    print("=" * 60)

    print()
    print(
        f"Clean transactions: "
        f"{len(transactions):,}"
    )

    print(
        f"Cancellations: "
        f"{len(cancellations):,}"
    )

    print(
        f"Unique customers: "
        f"{transactions['customer_id'].nunique():,}"
    )

    print(
        f"Unique invoices: "
        f"{transactions['invoice'].nunique():,}"
    )

    print(
        f"Unique products: "
        f"{transactions['stock_code'].nunique():,}"
    )

    print(
        f"Unique countries: "
        f"{transactions['country'].nunique():,}"
    )

    print()
    print(
        "Total transaction value: "
        f"£{transactions['transaction_amount'].sum():,.2f}"
    )

    print(
        "Total cancellation value: "
        f"£{cancellations['transaction_amount'].sum():,.2f}"
    )

    print()
    print("Output files:")

    print(
        f"  Transactions: "
        f"{TRANSACTIONS_PATH}"
    )

    print(
        f"  Cancellations: "
        f"{CANCELLATIONS_PATH}"
    )

    print(
        f"  Quality report: "
        f"{QUALITY_REPORT_PATH}"
    )

    print()
    print("Pipeline finished successfully.")


if __name__ == "__main__":
    main()