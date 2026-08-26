from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATASET_PATH = PROJECT_ROOT / "data" / "raw" / "online_retail_II.xlsx"

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


def load_dataset() -> pd.DataFrame:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}"
        )

    sheets = pd.read_excel(
        DATASET_PATH,
        sheet_name=None,
    )

    frames = []

    for sheet_name, frame in sheets.items():
        frame["source_sheet"] = sheet_name
        frames.append(frame)

    dataset = pd.concat(
        frames,
        ignore_index=True,
    )

    return dataset


def validate_schema(dataset: pd.DataFrame) -> None:
    missing_columns = [
        column
        for column in EXPECTED_COLUMNS
        if column not in dataset.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing expected columns: {missing_columns}"
        )


def dataset_summary(dataset: pd.DataFrame) -> dict:
    return {
        "rows": len(dataset),
        "columns": len(dataset.columns),
        "unique_invoices": dataset["Invoice"].nunique(),
        "unique_customers": dataset["Customer ID"].nunique(),
        "unique_products": dataset["StockCode"].nunique(),
        "unique_countries": dataset["Country"].nunique(),
        "missing_customer_ids": int(
            dataset["Customer ID"].isna().sum()
        ),
        "negative_quantity_rows": int(
            (dataset["Quantity"] < 0).sum()
        ),
        "zero_price_rows": int(
            (dataset["Price"] == 0).sum()
        ),
    }


if __name__ == "__main__":
    df = load_dataset()

    validate_schema(df)

    summary = dataset_summary(df)

    print("Dataset loaded successfully.")
    print()

    for key, value in summary.items():
        print(f"{key}: {value}")