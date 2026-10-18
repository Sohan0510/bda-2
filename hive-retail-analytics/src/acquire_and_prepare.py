"""
Dataset acquisition and preprocessing for the UCI Online Retail dataset.

Pipeline (reproducible, idempotent):
  1. Download the genuine UCI Online Retail Excel workbook if a verified copy
     is not already present in data/raw/.
  2. Verify the workbook is readable and contains the expected columns.
  3. Convert it to a Hive-friendly UTF-8 CSV in data/processed/.
  4. Clean/normalize values (dates, numerics, trimmed strings).
  5. Add transparent quality flags (cancellation, return, missing values,
     duplicates) -- records are NEVER removed automatically.
  6. Compute and save data-quality metrics as JSON.

The original workbook is preserved untouched so results can be reproduced.

Source:
  UCI Machine Learning Repository - Online Retail
  https://archive.ics.uci.edu/dataset/352/online+retail
  Direct file: https://archive.ics.uci.edu/ml/machine-learning-databases/00352/Online%20Retail.xlsx
  Attribution: Daqing Chen, Liang Sain synthesis? -- see README for citation.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
OUTPUTS_DIR = ROOT / "outputs" / "validation"

RAW_XLSX = RAW_DIR / "Online Retail.xlsx"
RAW_CSV_BACKUP = RAW_DIR / "Online Retail.csv"
PROCESSED_CSV = PROCESSED_DIR / "online_retail_clean.csv"
METRICS_JSON = OUTPUTS_DIR / "data_quality_metrics.json"

# Official UCI source
DATASET_URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/00352/Online%20Retail.xlsx"
DATASET_PAGE = "https://archive.ics.uci.edu/dataset/352/online+retail"

EXPECTED_COLUMNS = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
]

CHUNK_SIZE = 1024 * 1024  # 1 MiB


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Download (with resume support and graceful failure)
# ---------------------------------------------------------------------------
def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(block)
    return h.hexdigest()


def _looks_like_valid_xlsx(path: Path) -> bool:
    """Quick validity check: an xlsx is a zip starting with PK header."""
    try:
        with path.open("rb") as f:
            return f.read(4) == b"PK\x03\x04"
    except OSError:
        return False


def download_dataset(force: bool = False) -> Path:
    """
    Download the genuine dataset if needed.

    Returns the path to the verified raw workbook.
    Skips download when a valid copy already exists (idempotent).
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if RAW_XLSX.exists() and not force:
        if _looks_like_valid_xlsx(RAW_XLSX):
            log(f"Verified raw copy already present: {RAW_XLSX} "
                f"({RAW_XLSX.stat().st_size:,} bytes)")
            return RAW_XLSX
        log("Existing raw file is not a valid workbook; re-downloading.")

    tmp_path = RAW_XLSX.with_suffix(".xlsx.part")
    log(f"Downloading genuine dataset from {DATASET_URL}")

    req = urllib.request.Request(
        DATASET_URL,
        headers={"User-Agent": "Mozilla/5.0 (hive-retail-analytics project)"},
    )
    resume_from = tmp_path.stat().st_size if tmp_path.exists() else 0
    if resume_from:
        req.add_header("Range", f"bytes={resume_from}-")
        mode = "ab"
    else:
        mode = "wb"

    try:
        with urllib.request.urlopen(req, timeout=60) as resp, tmp_path.open(mode) as out:
            total = resp.headers.get("Content-Length")
            transferred = resume_from
            while True:
                chunk = resp.read(CHUNK_SIZE)
                if not chunk:
                    break
                out.write(chunk)
                transferred += len(chunk)
        os.replace(tmp_path, RAW_XLSX)
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        log(f"Download failed: {exc}")
        if tmp_path.exists() and tmp_path.stat().st_size > 0:
            log(f"Partial download preserved at {tmp_path} "
                f"({tmp_path.stat().st_size:,} bytes); re-run to resume.")
        if RAW_XLSX.exists() and _looks_like_valid_xlsx(RAW_XLSX):
            log("Falling back to previously valid raw copy.")
            return RAW_XLSX
        raise

    if not _looks_like_valid_xlsx(RAW_XLSX):
        raise RuntimeError("Downloaded file is not a valid Excel workbook")

    log(f"Downloaded and verified: {RAW_XLSX} ({RAW_XLSX.stat().st_size:,} bytes)")
    return RAW_XLSX


# ---------------------------------------------------------------------------
# Read + validate workbook
# ---------------------------------------------------------------------------
def read_workbook(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=0)
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Workbook missing expected columns: {missing}")
    log(f"Read workbook: {len(df):,} rows x {len(df.columns)} columns")
    return df


# ---------------------------------------------------------------------------
# Cleaning / normalization (records are preserved; only flags added)
# ---------------------------------------------------------------------------
def clean_and_flag(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # --- String columns: trim whitespace, preserve emptiness as NA where meaningful
    df["InvoiceNo"] = df["InvoiceNo"].astype(str).str.strip()
    df["StockCode"] = df["StockCode"].astype(str).str.strip()
    df["Country"] = df["Country"].astype(str).str.strip()
    # Description: keep NaN as NA (missing description), strip whitespace otherwise
    _desc_mask = df["Description"].notna()
    df.loc[_desc_mask, "Description"] = df.loc[_desc_mask, "Description"].astype(str).str.strip()
    # blank stockcode/country -> NA (none expected, but be safe)
    df.loc[df["StockCode"] == "", "StockCode"] = pd.NA
    df.loc[df["Country"] == "", "Country"] = pd.NA

    # --- InvoiceDate: parse consistently to ISO 'YYYY-MM-DD HH:MM:SS'
    parsed_dates = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    invalid_dates = parsed_dates.isna()
    if invalid_dates.any():
        log(f"WARNING: {int(invalid_dates.sum())} records have unparseable InvoiceDate")
    df["InvoiceDate"] = parsed_dates.dt.strftime("%Y-%m-%d %H:%M:%S")

    # --- Quantity: numeric integer
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").astype("Int64")
    invalid_qty = df["Quantity"].isna()
    if invalid_qty.any():
        log(f"WARNING: {int(invalid_qty.sum())} records have invalid Quantity")

    # --- UnitPrice: numeric decimal
    df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="coerce")
    invalid_price = df["UnitPrice"].isna()
    if invalid_price.any():
        log(f"WARNING: {int(invalid_price.sum())} records have invalid UnitPrice")

    # --- CustomerID: nullable integer (missing is meaningful, NOT dropped)
    df["CustomerID"] = pd.to_numeric(df["CustomerID"], errors="coerce").astype("Int64")

    # --- Transparent quality flags (records kept either way)
    df["is_cancellation"] = df["InvoiceNo"].str.startswith("C", na=False)
    df["is_return"] = df["Quantity"] < 0
    df["is_missing_description"] = df["Description"].isna()
    df["is_missing_customerid"] = df["CustomerID"].isna()
    df["is_duplicate"] = df.duplicated(
        subset=["InvoiceNo", "StockCode", "InvoiceDate", "Quantity", "UnitPrice", "Country"],
        keep=False,
    )
    # derived monetary value per line
    df["line_amount"] = (df["Quantity"].astype("float64") * df["UnitPrice"]).round(2)

    # Normalize serialized output forms
    df["CustomerID_out"] = df["CustomerID"].apply(
        lambda v: "" if pd.isna(v) else str(int(v))
    )
    df["Description_out"] = df["Description"].fillna("")
    df["Quantity_out"] = df["Quantity"].apply(
        lambda v: "" if pd.isna(v) else str(int(v))
    )
    df["UnitPrice_out"] = df["UnitPrice"].apply(
        lambda v: "" if pd.isna(v) else f"{v:.2f}"
    )
    df["InvoiceDate_out"] = df["InvoiceDate"].fillna("")

    out = pd.DataFrame(
        {
            "InvoiceNo": df["InvoiceNo"],
            "StockCode": df["StockCode"],
            "Description": df["Description_out"],
            "Quantity": df["Quantity_out"],
            "InvoiceDate": df["InvoiceDate_out"],
            "UnitPrice": df["UnitPrice_out"],
            "CustomerID": df["CustomerID_out"],
            "Country": df["Country"],
            "is_cancellation": df["is_cancellation"].map({True: "true", False: "false"}),
            "is_return": df["is_return"].map({True: "true", False: "false"}),
            "is_missing_description": df["is_missing_description"].map(
                {True: "true", False: "false"}
            ),
            "is_missing_customerid": df["is_missing_customerid"].map(
                {True: "true", False: "false"}
            ),
            "is_duplicate": df["is_duplicate"].map({True: "true", False: "false"}),
            "line_amount": df["line_amount"].apply(
                lambda v: "" if pd.isna(v) else f"{v:.2f}"
            ),
        }
    )
    return out


# ---------------------------------------------------------------------------
# Quality metrics
# ---------------------------------------------------------------------------
def compute_metrics(raw_df: pd.DataFrame, clean_df: pd.DataFrame) -> dict:
    metrics = {
        "generated_at": datetime.now().isoformat(),
        "source_url": DATASET_URL,
        "source_page": DATASET_PAGE,
        "raw_records": int(len(raw_df)),
        "processed_records": int(len(clean_df)),
        "distinct_invoices": int(raw_df["InvoiceNo"].nunique()),
        "distinct_products": int(raw_df["StockCode"].nunique()),
        "distinct_countries": int(raw_df["Country"].nunique()),
        "identified_customers": int(raw_df["CustomerID"].nunique()),
        "missing_values_by_column": {
            col: int(raw_df[col].isna().sum()) for col in EXPECTED_COLUMNS
        },
        "duplicate_records": int(raw_df.duplicated().sum()),
        "invalid_dates": int(
            pd.to_datetime(raw_df["InvoiceDate"], errors="coerce").isna().sum()
        ),
        "invalid_quantity": int(
            pd.to_numeric(raw_df["Quantity"], errors="coerce").isna().sum()
        ),
        "invalid_unitprice": int(
            pd.to_numeric(raw_df["UnitPrice"], errors="coerce").isna().sum()
        ),
        "cancellation_invoices_distinct": int(
            raw_df.loc[raw_df["InvoiceNo"].astype(str).str.startswith("C", na=False), "InvoiceNo"].nunique()
        ),
        "cancellation_lines": int(
            raw_df["InvoiceNo"].astype(str).str.startswith("C", na=False).sum()
        ),
        "negative_quantity_records": int((pd.to_numeric(raw_df["Quantity"], errors="coerce") < 0).sum()),
        "zero_quantity_records": int((pd.to_numeric(raw_df["Quantity"], errors="coerce") == 0).sum()),
        "unitprice_le_zero": int((pd.to_numeric(raw_df["UnitPrice"], errors="coerce") <= 0).sum()),
        "unitprice_negative": int((pd.to_numeric(raw_df["UnitPrice"], errors="coerce") < 0).sum()),
        "missing_stockcode": int(raw_df["StockCode"].isna().sum()),
        "missing_description": int(raw_df["Description"].isna().sum()),
        "missing_customerid": int(raw_df["CustomerID"].isna().sum()),
        "earliest_valid_transaction_date": str(
            pd.to_datetime(raw_df["InvoiceDate"], errors="coerce").min()
        ),
        "latest_valid_transaction_date": str(
            pd.to_datetime(raw_df["InvoiceDate"], errors="coerce").max()
        ),
        "total_quantity_recorded": float(
            pd.to_numeric(raw_df["Quantity"], errors="coerce").sum()
        ),
        "final_records_available_for_analysis": int(len(clean_df)),
    }
    metrics["records_excluded"] = metrics["raw_records"] - metrics["final_records_available_for_analysis"]
    return metrics


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    force = "--force" in sys.argv
    try:
        xlsx_path = download_dataset(force=force)
    except Exception as exc:  # noqa: BLE001
        log(f"FATAL: could not acquire dataset: {exc}")
        return 1

    try:
        raw_df = read_workbook(xlsx_path)
    except Exception as exc:  # noqa: BLE001
        log(f"FATAL: could not read workbook: {exc}")
        return 1

    clean_df = clean_and_flag(raw_df)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(PROCESSED_CSV, index=False, encoding="utf-8")
    log(f"Wrote processed CSV: {PROCESSED_CSV} ({len(clean_df):,} rows)")

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    metrics = compute_metrics(raw_df, clean_df)
    METRICS_JSON.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    log(f"Wrote quality metrics: {METRICS_JSON}")

    # Console summary
    print("\n=== Data quality summary ===")
    for k, v in metrics.items():
        print(f"  {k}: {v}")
    print("==========================\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
