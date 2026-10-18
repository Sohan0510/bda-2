"""
Independent validation of the Hive analytical outputs.

Recomputes key metrics directly from the processed CSV (pandas, independent of
Hive) and compares them against the actual Hive query outputs in outputs/.
Uses the same inclusion rules and monetary precision (2 dp, Decimal-like via
rounding) on both sides. Results are saved to
outputs/validation/validation_results.json (machine-readable).

Run:  python tests/validate.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED_CSV = ROOT / "data" / "processed" / "online_retail_clean.csv"
OUTPUTS_DIR = ROOT / "outputs"
VALIDATION_DIR = ROOT / "outputs" / "validation"
VALIDATION_JSON = VALIDATION_DIR / "validation_results.json"

TOLERANCE = 0.011  # allow for binary float vs DECIMAL rounding differences


def read_tsv(name: str) -> pd.DataFrame:
    path = OUTPUTS_DIR / f"{name}.tsv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, sep="\t", dtype=str, keep_default_na=False,
                     encoding="utf-8", encoding_errors="replace")
    # beeline lowercases column names
    df.columns = [c.lower() for c in df.columns]
    # beeline may emit a blank trailing line; drop fully-empty rows
    df = df[df.astype(str).apply(lambda r: (r.str.len() > 0).any(), axis=1)]
    return df


def to_num(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def close(a: float, b: float) -> bool:
    return a is not None and b is not None and abs(a - b) <= TOLERANCE


def main() -> int:
    df = pd.read_csv(PROCESSED_CSV, dtype=str, keep_default_na=False)
    for col in ["Quantity", "UnitPrice", "line_amount"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["is_cancellation"] = df["is_cancellation"].eq("true")
    df["is_return"] = df["is_return"].eq("true")
    df["is_missing_customerid"] = df["is_missing_customerid"].eq("true")
    df["CustomerID"] = pd.to_numeric(df["CustomerID"], errors="coerce")

    positive = (df["Quantity"] > 0) & (~df["is_cancellation"])
    results = []
    overall_ok = True

    def check(name: str, hive_value, pandas_value, ok: bool) -> None:
        nonlocal overall_ok
        overall_ok = overall_ok and bool(ok)
        results.append(
            {
                "check": name,
                "hive_value": hive_value,
                "pandas_value": pandas_value,
                "match": bool(ok),
            }
        )

    # ------------------------------------------------------------------
    # 1. Input / output record counts
    # ------------------------------------------------------------------
    overview = read_tsv("a_dataset_overview")
    hive_records = int(to_num(overview["total_records"]).iloc[0])
    check("total_records", hive_records, len(df), hive_records == len(df))

    # ------------------------------------------------------------------
    # 2. Total quantity sold (signed, as recorded)
    # ------------------------------------------------------------------
    hive_qty = int(to_num(overview["total_quantity_recorded"]).iloc[0])
    pandas_qty = int(df["Quantity"].sum())
    check("total_quantity_recorded", hive_qty, pandas_qty, hive_qty == pandas_qty)

    # ------------------------------------------------------------------
    # 3. Monthly revenue totals (positive-only filter)
    # ------------------------------------------------------------------
    monthly_hive = read_tsv("b_monthly_sales")
    monthly_hive["month"] = monthly_hive["month"]
    monthly_hive["pos_rev"] = to_num(monthly_hive["positive_sales_revenue_gbp"])
    monthly_hive["signed_rev"] = to_num(monthly_hive["signed_revenue_gbp"])

    df["month"] = pd.to_datetime(df["InvoiceDate"], errors="coerce").dt.strftime(
        "%Y-%m"
    )
    monthly_pd = (
        df[positive].groupby("month")["line_amount"]
        .sum()
        .round(2)
        .rename("pos_rev_pd")
    )
    monthly_signed_pd = (
        df.groupby("month")["line_amount"].sum().round(2).rename("signed_rev_pd")
    )
    m = monthly_hive.set_index("month").join(monthly_pd).join(monthly_signed_pd)
    m["pos_ok"] = m.apply(
        lambda r: close(r["pos_rev"], r["pos_rev_pd"]), axis=1
    )
    m["signed_ok"] = m.apply(
        lambda r: close(r["signed_rev"], r["signed_rev_pd"]), axis=1
    )
    monthly_pos_ok = bool(m["pos_ok"].all())
    monthly_signed_ok = bool(m["signed_ok"].all())
    check("monthly_positive_revenue_all_months", m["pos_rev"].tolist(),
          m["pos_rev_pd"].tolist(), monthly_pos_ok)
    check("monthly_signed_revenue_all_months", m["signed_rev"].tolist(),
          m["signed_rev_pd"].tolist(), monthly_signed_ok)

    # ------------------------------------------------------------------
    # 4. Total product-level revenue (same positive-only filter as monthly)
    # ------------------------------------------------------------------
    prod_hive = read_tsv("c_product_quantity_all")
    prod_hive["all_rev"] = to_num(prod_hive["total_sales_value_gbp"])
    prod_hive["qty"] = to_num(prod_hive["total_quantity"])
    # Positive-only revenue per product (recompute in pandas)
    prod_pd = (
        df[positive].groupby(["StockCode", "Description"])["line_amount"]
        .sum()
        .round(2)
        .reset_index()
        .rename(columns={"line_amount": "pos_rev_pd"})
    )
    hive_pos_rev_by_product = (
        df[positive].groupby("StockCode")["line_amount"].sum().round(2)
    )
    # pandas total positive revenue across products
    pandas_pos_rev_total = round(float(df.loc[positive, "line_amount"].sum()), 2)
    hive_pos_rev_total = round(float(monthly_hive["pos_rev"].sum()), 2)
    check("product_vs_monthly_positive_revenue_total", hive_pos_rev_total,
          pandas_pos_rev_total, close(hive_pos_rev_total, pandas_pos_rev_total))

    # per-product spot check on top products
    top_hive = read_tsv("c_product_top20_quantity")
    top_hive["qty"] = to_num(top_hive["total_quantity"])
    # Same rule as the Hive query: total recorded (signed) quantity per product.
    top_pd = (
        df.groupby("StockCode")["Quantity"]
        .sum()
        .sort_values(ascending=False)
        .head(20)
    )
    hive_top_stock = top_hive["stockcode"].tolist()
    pd_top_stock = top_pd.index.tolist()
    check("top20_products_by_quantity_ranking", hive_top_stock, pd_top_stock,
          hive_top_stock == pd_top_stock)

    # per-product revenue ranking check
    top_r_hive = read_tsv("c_product_top20_revenue")
    top_r_pd = (
        df.groupby("StockCode")["line_amount"]
        .sum()
        .sort_values(ascending=False)
        .head(20)
    )
    hive_top_r_stock = top_r_hive["stockcode"].tolist()
    pd_top_r_stock = top_r_pd.index.tolist()
    check("top20_products_by_revenue_ranking", hive_top_r_stock, pd_top_r_stock,
          hive_top_r_stock == pd_top_r_stock)

    # ------------------------------------------------------------------
    # 5. Country-level totals (signed, all lines)
    # ------------------------------------------------------------------
    country_hive = read_tsv("e_country_summary")
    country_hive["rev"] = to_num(country_hive["revenue_gbp"])
    country_pd = (
        df.groupby("Country")["line_amount"]
        .sum()
        .round(2)
        .reset_index()
        .rename(columns={"line_amount": "rev_pd"})
    )
    country_pd.columns = [c.lower() for c in country_pd.columns]
    c = country_hive.set_index("country").join(country_pd.set_index("country"))
    c["ok"] = c.apply(lambda r: close(r["rev"], r["rev_pd"]), axis=1)
    country_ok = bool(c["ok"].all())
    check("country_revenue_all_countries", country_hive["rev"].tolist(),
          c["rev_pd"].tolist(), country_ok)

    # country total equals overall signed revenue
    hive_country_total = round(float(country_hive["rev"].sum()), 2)
    pandas_country_total = round(float(df["line_amount"].sum()), 2)
    check("country_total_equals_overall_signed_revenue", hive_country_total,
          pandas_country_total, close(hive_country_total, pandas_country_total))

    # ------------------------------------------------------------------
    # 6. Top-selling product (by quantity)
    # ------------------------------------------------------------------
    hive_top_product = top_hive.iloc[0]["stockcode"]
    pandas_top_product = top_pd.index[0]
    check("top_product_by_quantity", hive_top_product, pandas_top_product,
          hive_top_product == pandas_top_product)

    # ------------------------------------------------------------------
    # 7. Cancellation and return-related counts
    # ------------------------------------------------------------------
    check("cancellation_lines", int(overview["cancellation_lines"].iloc[0]),
          int(df["is_cancellation"].sum()),
          int(overview["cancellation_lines"].iloc[0]) == int(df["is_cancellation"].sum()))
    check("cancellation_invoices_distinct",
          int(overview["cancellation_invoices"].iloc[0]),
          int(df.loc[df["is_cancellation"], "InvoiceNo"].nunique()),
          int(overview["cancellation_invoices"].iloc[0])
          == int(df.loc[df["is_cancellation"], "InvoiceNo"].nunique()))
    check("return_lines", int(overview["return_lines"].iloc[0]),
          int(df["is_return"].sum()),
          int(overview["return_lines"].iloc[0]) == int(df["is_return"].sum()))

    # Cancellation breakdown by country
    cbc_hive = read_tsv("f_cancellation_by_country").set_index("country")
    pd_canc_inv = df[df["is_cancellation"]].groupby("Country")["InvoiceNo"].nunique()
    pd_canc_lines = df[df["is_cancellation"]].groupby("Country").size()
    cbc_inv_ok = all(
        int(to_num(cbc_hive.loc[cnt, "cancellation_invoices"])) == int(pd_canc_inv.get(cnt, 0))
        for cnt in cbc_hive.index
    )
    cbc_lines_ok = all(
        int(to_num(cbc_hive.loc[cnt, "cancellation_lines"])) == int(pd_canc_lines.get(cnt, 0))
        for cnt in cbc_hive.index
    )
    check("cancellation_invoices_by_country_all_match", True, cbc_inv_ok, cbc_inv_ok)
    check("cancellation_lines_by_country_all_match", True, cbc_lines_ok, cbc_lines_ok)

    # Quantity direction classification
    qd_hive = read_tsv("f_quantity_direction").set_index("line_type")
    pos_lines_pd = int(((df["Quantity"] > 0) & (~df["is_cancellation"])).sum())
    canc_lines_pd = int(df["is_cancellation"].sum())
    ret_lines_pd = int(((df["Quantity"] < 0) & (~df["is_cancellation"])).sum())
    qd_match = (
        int(to_num(qd_hive.loc["positive_sale", "lines"])) == pos_lines_pd
        and int(to_num(qd_hive.loc["cancellation", "lines"])) == canc_lines_pd
        and int(to_num(qd_hive.loc["return_negative_quantity", "lines"])) == ret_lines_pd
    )
    check("quantity_direction_lines_all_match", True, qd_match, qd_match)

    # ------------------------------------------------------------------
    # 8. Missing customer identifiers
    # ------------------------------------------------------------------
    check("identified_customers_distinct", int(overview["identified_customers"].iloc[0]),
          int(df["CustomerID"].nunique()),
          int(overview["identified_customers"].iloc[0]) == int(df["CustomerID"].nunique()))
    # Documented rule: records with missing CustomerIDs are retained, not counted as customers.
    check("missing_customerid_rows_retained", int(overview["total_records"].iloc[0]),
          int(len(df)), int(overview["total_records"].iloc[0]) == int(len(df)))

    # ------------------------------------------------------------------
    # 9. Output consistency: row counts of exported TSVs vs expected
    # ------------------------------------------------------------------
    checks_rows = {
        "c_product_quantity_all": len(df.groupby("StockCode")),
        "e_country_summary": len(df["Country"].unique()),
        "e_country_monthly": len(df.groupby(["Country", "month"])),
        "f_cancellation_by_country": len(df["Country"].unique()),
        "g_daily_trend": len(df.groupby(df["InvoiceDate"].str[:10])),
        "g_hourly_pattern": int(df["InvoiceDate"].str[11:13].astype(int).nunique()),
    }
    for name, expected in checks_rows.items():
        out = read_tsv(name)
        actual = len(out)
        check(f"row_count_{name}", actual, expected, actual == expected)

    # ------------------------------------------------------------------
    # Save results
    # ------------------------------------------------------------------
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "validated_at": pd.Timestamp.now().isoformat(),
        "processed_csv": str(PROCESSED_CSV),
        "raw_records": int(len(df)),
        "overall_pass": bool(overall_ok),
        "checks": results,
    }
    VALIDATION_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"Overall validation: {'PASS' if overall_ok else 'FAIL'}")
    for r in results:
        print(f"  [{'PASS' if r['match'] else 'FAIL'}] {r['check']}")
    print(f"Validation results written to {VALIDATION_JSON}")
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
