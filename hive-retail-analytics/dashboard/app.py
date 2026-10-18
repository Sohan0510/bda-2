"""
Interactive dashboard for the Hive Retail Analytics project.

IMPORTANT: every metric shown here is computed by Apache HiveQL queries against
the genuine UCI Online Retail dataset and saved to outputs/ by run_analytics.ps1.
This dashboard is a presentation layer only -- it contains no hardcoded numbers
and performs no aggregation of its own beyond re-shaping the Hive outputs.

Run:
    streamlit run dashboard/app.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"


def tsv(name: str) -> pd.DataFrame:
    """Load a Hive query output TSV; empty frame if unavailable."""
    path = OUTPUTS / f"{name}.tsv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, sep="\t", dtype=str, encoding="utf-8", encoding_errors="replace")
    df.columns = [c.strip().lower() for c in df.columns]
    # drop fully-empty trailing rows
    df = df[df.astype(str).apply(lambda r: (r.str.len() > 0).any(), axis=1)].reset_index(drop=True)
    return df


def num(df: pd.DataFrame, col: str) -> pd.DataFrame:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


st.set_page_config(page_title="Retail Analytics (Apache Hive)", layout="wide")
st.title("Large-Scale Customer Transaction Analysis -- Apache Hive")
st.caption(
    "Genuine UCI Online Retail dataset (541,909 transaction lines, "
    "2010-12 to 2011-12). All metrics computed by Apache Hive queries "
    "(see hive/*.hql) and loaded from outputs/."
)

# --------------------------------------------------------------------------
# Availability check
# --------------------------------------------------------------------------
overview = tsv("a_dataset_overview")
if overview.empty:
    st.error(
        "Hive outputs not found. Start Hive, load the data and run the "
        "analytics scripts first (run_analytics.ps1)."
    )
    st.stop()

# --------------------------------------------------------------------------
# Sidebar filters (apply to real Hive outputs)
# --------------------------------------------------------------------------
st.sidebar.header("Filters")

countries = tsv("e_country_summary")
countries = num(countries, "revenue_gbp")
country_options = ["All"] + sorted([c for c in countries["country"].dropna().unique()])
country = st.sidebar.selectbox("Country", country_options, index=0)

products = tsv("c_product_quantity_all")
products = num(products, "total_quantity")
product_options = ["All"] + sorted([p for p in products["stockcode"].dropna().unique()])
product = st.sidebar.selectbox("Product (StockCode)", product_options, index=0)

daily = tsv("g_daily_trend")
daily = num(daily, "positive_sales_revenue_gbp")
if not daily.empty and "transaction_date" in daily.columns:
    daily["transaction_date"] = pd.to_datetime(daily["transaction_date"], errors="coerce")
    date_min = daily["transaction_date"].min().date()
    date_max = daily["transaction_date"].max().date()
    date_range = st.sidebar.date_input(
        "Date range (daily trend)", value=(date_min, date_max), min_value=date_min, max_value=date_max
    )
else:
    date_range = None

# --------------------------------------------------------------------------
# Overview
# --------------------------------------------------------------------------
row = overview.iloc[0]
st.header("Overview")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Transaction records", f"{int(row['total_records']):,}")
c2.metric("Distinct invoices", f"{int(row['distinct_invoices']):,}")
c3.metric("Distinct products", f"{int(row['distinct_products']):,}")
c4.metric("Identified customers", f"{int(row['identified_customers']):,}")
c5.metric("Total quantity recorded", f"{int(row['total_quantity_recorded']):,}")

st.markdown(
    f"**Period:** {row['earliest_transaction_date']} to {row['latest_transaction_date']}  "
    f"| **Countries:** {int(row['distinct_countries'])}  "
    f"| **Cancellation lines:** {int(row['cancellation_lines']):,} "
    f"({int(row['cancellation_invoices'])} distinct cancelled invoices)  "
    f"| **Return-related lines:** {int(row['return_lines']):,}"
)
st.info(
    "Cancellations (InvoiceNo starting with 'C') and returns (negative Quantity) "
    "are retained in the data and flagged; they are excluded from positive-sales "
    "totals where stated."
)

# --------------------------------------------------------------------------
# Monthly sales
# --------------------------------------------------------------------------
st.header("Monthly Sales")
monthly = tsv("b_monthly_sales")
monthly = num(monthly, ["signed_revenue_gbp", "positive_sales_revenue_gbp",
                        "quantity_sold", "positive_sales_quantity",
                        "transaction_lines", "distinct_invoices",
                        "cancellation_adjustment_gbp"])
if not monthly.empty:
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly["month"], y=monthly["positive_sales_revenue_gbp"],
                         name="Positive sales revenue (GBP)"))
    fig.add_trace(go.Scatter(x=monthly["month"], y=monthly["signed_revenue_gbp"],
                             mode="lines+markers", name="Signed revenue (incl. cancellations/returns) (GBP)"))
    fig.update_layout(barmode="group", xaxis_title="Month", yaxis_title="GBP",
                      legend_title="Measure", height=450)
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=monthly["month"], y=monthly["quantity_sold"], name="Quantity (signed)"))
    fig2.add_trace(go.Bar(x=monthly["month"], y=monthly["positive_sales_quantity"], name="Positive-sales quantity"))
    fig2.update_layout(barmode="group", xaxis_title="Month", yaxis_title="Units", height=400)
    st.plotly_chart(fig2, use_container_width=True)
    st.dataframe(monthly, use_container_width=True, hide_index=True)
else:
    st.warning("Monthly sales output unavailable.")

# --------------------------------------------------------------------------
# Product analytics
# --------------------------------------------------------------------------
st.header("Product Analytics")
col1, col2 = st.columns(2)
top_q = tsv("c_product_top20_quantity")
top_q = num(top_q, ["total_quantity", "total_sales_value_gbp"])
top_r = tsv("c_product_top20_revenue")
top_r = num(top_r, ["total_sales_value_gbp", "total_quantity"])
if not top_q.empty:
    fig = px.bar(top_q.sort_values("total_quantity"), x="total_quantity", y="description",
                 orientation="h", labels={"total_quantity": "Quantity", "description": "Product"},
                 title="Top 20 products by quantity recorded")
    st.plotly_chart(fig, use_container_width=True)
if not top_r.empty:
    fig = px.bar(top_r.sort_values("total_sales_value_gbp"), x="total_sales_value_gbp", y="description",
                 orientation="h", labels={"total_sales_value_gbp": "Revenue (GBP)", "description": "Product"},
                 title="Top 20 products by revenue (GBP)")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Product table (all products)")
if not products.empty:
    pview = products.copy()
    if product != "All":
        pview = pview[pview["stockcode"] == product]
    st.dataframe(pview, use_container_width=True, hide_index=True)

cat = tsv("d_category_analysis")
cat = num(cat, ["total_quantity_sold", "total_revenue_gbp"])
if not cat.empty:
    st.subheader("Derived product categories (not supplied by the dataset)")
    fig = px.bar(cat.sort_values("total_revenue_gbp"), x="total_revenue_gbp", y="product_category",
                 orientation="h", labels={"total_revenue_gbp": "Revenue (GBP)", "product_category": "Derived category"},
                 title="Revenue by derived category")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(cat, use_container_width=True, hide_index=True)

# --------------------------------------------------------------------------
# Geographical analysis
# --------------------------------------------------------------------------
st.header("Geographical Analysis")
countries = num(countries, ["quantity_sold", "transaction_lines", "distinct_invoices", "identified_customers"])
if not countries.empty:
    cview = countries[countries["country"] != "Unspecified"].copy()
    if country != "All":
        cview = cview[cview["country"] == country]
    fig = px.bar(cview.sort_values("revenue_gbp", ascending=True).tail(15),
                 x="revenue_gbp", y="country", orientation="h",
                 labels={"revenue_gbp": "Revenue (GBP)", "country": "Country"},
                 title="Top 15 countries by revenue (GBP)")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(cview.sort_values("revenue_gbp", ascending=False),
                 use_container_width=True, hide_index=True)

cm = tsv("e_country_monthly")
cm = num(cm, ["revenue_gbp", "quantity_sold"])
if not cm.empty:
    st.subheader("Country-wise monthly revenue trend")
    if country != "All":
        cm = cm[cm["country"] == country]
    fig = px.line(cm, x="month", y="revenue_gbp", color="country",
                  labels={"revenue_gbp": "Revenue (GBP)", "month": "Month"},
                  title="Monthly revenue by country (GBP)")
    st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------------------------
# Transaction quality
# --------------------------------------------------------------------------
st.header("Transaction Quality")
fc = tsv("f_cancellation_summary")
fq = tsv("f_quantity_direction")
fe = tsv("f_revenue_effect")
q1, q2, q3 = st.columns(3)
if not fc.empty:
    r = fc.iloc[0]
    q1.metric("Cancelled invoices (distinct)", f"{int(r['cancellation_invoices_distinct']):,}")
    q1.metric("Cancellation lines", f"{int(r['cancellation_lines']):,}")
if not fq.empty:
    pos = fq[fq["line_type"] == "positive_sale"]
    neg = fq[fq["line_type"] == "return_negative_quantity"]
    can = fq[fq["line_type"] == "cancellation"]
    q2.metric("Positive-sale lines", f"{int(pos['lines'].iloc[0]) if not pos.empty else 0:,}")
    q2.metric("Return (negative qty) lines", f"{int(neg['lines'].iloc[0]) if not neg.empty else 0:,}")
    q2.metric("Cancellation lines", f"{int(can['lines'].iloc[0]) if not can.empty else 0:,}")
if not fe.empty:
    r = fe.iloc[0]
    q3.metric("Gross signed value (GBP)", f"{float(r['gross_signed_value_gbp']):,.2f}")
    q3.metric("Positive-sales value (GBP)", f"{float(r['positive_sales_value_gbp']):,.2f}")

st.subheader("Data quality summary (from preprocessing)")
st.write("See outputs/validation/data_quality_metrics.json for the full preprocessing quality report.")
st.dataframe(tsv("g_weekday_weekend"), use_container_width=True, hide_index=True)
st.dataframe(tsv("g_hourly_pattern"), use_container_width=True, hide_index=True)

# --------------------------------------------------------------------------
# Additional insights
# --------------------------------------------------------------------------
st.header("Additional Insights")
if not daily.empty:
    dd = daily.copy()
    if date_range and len(date_range) == 2:
        dd = dd[(dd["transaction_date"].dt.date >= pd.Timestamp(date_range[0]).date()) &
                (dd["transaction_date"].dt.date <= pd.Timestamp(date_range[1]).date())]
    fig = px.line(dd, x="transaction_date", y="positive_sales_revenue_gbp",
                  labels={"positive_sales_revenue_gbp": "Revenue (GBP)", "transaction_date": "Date"},
                  title="Daily positive-sales revenue trend (GBP)")
    st.plotly_chart(fig, use_container_width=True)

gc = tsv("g_customer_txn_distribution")
gc = num(gc, ["identified_customers", "total_invoices"])
if not gc.empty:
    fig = px.bar(gc, x="transaction_count_band", y="identified_customers",
                 labels={"identified_customers": "Identified customers", "transaction_count_band": "Transactions per customer"},
                 title="Distribution of identified customers by transaction count")
    st.plotly_chart(fig, use_container_width=True)

gr = tsv("g_repeat_activity")
if not gr.empty:
    r = gr.iloc[0]
    st.write(
        f"Identified customers: {r['identified_customers']} | "
        f"Avg invoices per customer: {r['avg_invoices_per_customer']} | "
        f"Customers with repeat invoices: {r['customers_with_repeat_invoices']}"
    )

st.divider()
st.caption(
    "Categories are derived from transparent keyword rules (config/category_rules.csv) and are "
    "not supplied by the dataset. No customer attributes (age, gender, motives) are inferred."
)
