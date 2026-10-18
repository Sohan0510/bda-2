# Large-Scale Customer Transaction and Purchase Pattern Analysis Using Apache Hive

(Big Data Analytics Mini-Project using Apache Hive & Genuine UCI Retail Dataset)

## What this is

A complete, tested, reproducible mini-project that analyses the **genuine UCI
Machine Learning Repository "Online Retail" dataset** with **Apache Hive** as
the primary analytical engine. It identifies monthly sales trends, product
demand, top-selling items, country-wise sales patterns, cancellations/returns
and data-quality statistics — with every metric computed by executable HiveQL
and independently validated with Python.

No synthetic data, no hardcoded results, no academic report.

## Genuine dataset

* **Source:** UCI Machine Learning Repository – Online Retail
  https://archive.ics.uci.edu/dataset/352/online+retail
* **Direct file:** https://archive.ics.uci.edu/ml/machine-learning-databases/00352/Online%20Retail.xlsx
* **Records:** 541,909 transaction lines (December 2010 – December 2011)
* **Attribution:** UCI Machine Learning Repository (Online Retail data set).
  The original workbook is preserved under `data/raw/` and is never modified.

## Project structure

```
hive-retail-analytics/
├── docker-compose.yml          # Apache Hive 4.0.0 service (HiveServer2 +
│                               # embedded Derby metastore, named volumes)
├── requirements.txt            # Python dependencies
├── README.md                   # this file
├── backend/                    # FastAPI async REST API backend
│   └── main.py                 # REST endpoints, Hive data loaders, OpenAPI
├── config/
│   └── category_rules.csv      # Derived (documented) product-category rules
├── dashboard/
│   └── app.py                  # Streamlit dashboard consuming Hive outputs
├── data/
│   ├── raw/                    # Original downloaded workbook (preserved)
│   └── processed/              # Prepared CSV for Hive (generated)
├── frontend/                   # Modern responsive Single Page Web Application
│   ├── index.html              # Semantic HTML5 app with tabbed navigation
│   ├── css/style.css           # Luxury obsidian dark glassmorphism stylesheet
│   └── js/app.js               # Client controller, Chart.js graphs, catalog search
├── hive/                       # HiveQL scripts (run in numbered order)
│   ├── 01_create_database.hql
│   ├── 02_create_tables.hql
│   ├── 03_load_data.hql
│   ├── 04_clean_transform.hql
│   ├── a_dataset_overview.hql
│   ├── b_monthly_sales.hql
│   ├── c_product_quantity_all.hql
│   ├── c_product_top20_quantity.hql
│   ├── c_product_top20_revenue.hql
│   ├── c_product_low_volume.hql
│   ├── d_category_analysis.hql
│   ├── e_country_summary.hql
│   ├── e_country_monthly.hql
│   ├── f_cancellation_summary.hql
│   ├── f_quantity_direction.hql
│   ├── f_revenue_effect.hql
│   ├── f_cancellation_by_country.hql
│   ├── g_daily_trend.hql
│   ├── g_weekday_weekend.hql
│   ├── g_hourly_pattern.hql
│   ├── g_avg_transaction_value.hql
│   ├── g_customer_txn_distribution.hql
│   └── g_repeat_activity.hql
├── outputs/                    # Actual Hive query results (TSV, generated)
├── outputs/validation/
│   ├── data_quality_metrics.json
│   └── validation_results.json
├── run_analytics.ps1           # Executes all analytics scripts, saves outputs
├── src/
│   └── acquire_and_prepare.py  # Dataset acquisition + preprocessing
└── tests/
    └── validate.py             # Independent validation of Hive outputs
```

## Environment tested

* Windows 11, Docker Desktop (Docker 29.8.2, Compose v5.6.0), Python 3.14.7
* Apache Hive **4.0.0** (official `apache/hive:4.0.0` image), HiveServer2 on port 10000,
  embedded Derby metastore, local filesystem warehouse (no HDFS claim).
* Beeline client for query execution.

## Prerequisites

* Docker Desktop running.
* Python 3 with: `pip install -r requirements.txt` (pandas, openpyxl, streamlit,
  plotly, pyarrow, numpy).

## Setup and execution (PowerShell)

Run from the project folder `hive-retail-analytics/`.

### 1. Start Hive

```powershell
docker compose up -d
```

Wait for HiveServer2 to become ready (about a minute):

```powershell
docker compose logs -f hive-server
```

Look for "Starting HiveServer2". Verify with Beeline:

```powershell
docker exec hive-server beeline -u jdbc:hive2://localhost:10000 --showHeader=false --silent=true -e "SHOW DATABASES;"
```

Expected: `default` and `retail_analytics` (after step 2).

To stop/restart later: `docker compose down` then `docker compose up -d`.
Data and metadata persist in the named volumes `hive_warehouse` and `hive_metastore`.

### 2. Acquire and prepare the dataset

```powershell
python src\acquire_and_prepare.py
```

This (a) downloads the genuine UCI workbook only if a valid copy is not already
present in `data/raw/` (resumable, idempotent), (b) verifies it is readable,
(c) converts it to `data/processed/online_retail_clean.csv`, (d) adds transparent
quality flags (no records are removed automatically), and (e) writes
`outputs/validation/data_quality_metrics.json`.

### 3. Copy data and scripts into the container, create schema, load, transform

```powershell
docker cp data\processed\online_retail_clean.csv hive-server:/tmp/online_retail_clean.csv
docker cp config\category_rules.csv hive-server:/tmp/category_rules.csv
docker cp hive hive-server:/tmp/hive-scripts   # copies scripts into /tmp/hive-scripts/*.hql
docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -f /tmp/hive-scripts/01_create_database.hql
docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -f /tmp/hive-scripts/02_create_tables.hql
docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -f /tmp/hive-scripts/03_load_data.hql
docker exec hive-server beeline -u jdbc:hive2://localhost:10000 -f /tmp/hive-scripts/04_clean_transform.hql
```

All load/transform scripts are idempotent (`TRUNCATE` before load, `INSERT
OVERWRITE` for the analytical table), so they can be re-run safely.

### 4. Execute the analytical queries and save outputs

```powershell
.\run_analytics.ps1
```

Runs every HiveQL analytics script through Beeline and writes machine-readable
TSV results to `outputs/`.

### 5. Validate the results

```powershell
python tests\validate.py
```

Independently recomputes key metrics from the processed CSV and compares them
against the actual Hive outputs (record counts, total quantity, monthly revenue,
product/country totals, top-product rankings, cancellation counts, missing-CustomerID
handling, output row counts). Writes `outputs/validation/validation_results.json`.

All checks pass against the genuine dataset.

### 6. Launch the Full-Stack Modern Web Application & REST API (Recommended)

Run the FastAPI backend (serves both the REST API and the modern responsive frontend):

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
```

* **Web Application:** http://localhost:8080 (Luxury Obsidian Dark Glassmorphic dashboard with Chart.js canvas visualizations, live product search, catalog pagination, interactive country trends, data quality audit, and HiveQL studio).
* **Interactive API Documentation (Swagger):** http://localhost:8080/docs
* **Alternative Streamlit Dashboard:**
  ```powershell
  python -m streamlit run dashboard\app.py
  ```
  Accessible at http://localhost:8501.

## Analytics implemented (HiveQL)

* **A. Dataset overview** – record, invoice, product, country and identified-customer
  counts; date range; total quantity; cancellation/return counts.
* **B. Monthly sales** – revenue (signed and positive-only), quantities, invoice
  volumes, cancellation adjustments, in GBP.
* **C. Product analysis** – quantity and revenue by StockCode/Description; top 20
  by quantity; top 20 by revenue; low-volume products. Description variants are
  never merged or silently dropped.
* **D. Category analysis** – derived categories from transparent rules in
  `config/category_rules.csv`; explicit `Unclassified` bucket; clearly labelled
  as derived (the dataset supplies no categories).
* **E. Country analysis** – revenue, quantity, transactions, identified customers
  by country; monthly country trends.
* **F. Cancellation/return analysis** – invoice-level vs line-level counts,
  positive vs negative quantities, monetary effect on totals, by country.
* **G. Additional insights** – daily trends, weekday/weekend, hourly patterns,
  average transaction value, customer transaction-count distribution, repeat
  activity.

## Key results (genuine dataset, verified by Hive + independent validation)

* 541,909 records; 25,900 distinct invoices; 4,070 distinct products; 38 countries;
  4,372 identified customers (missing CustomerIDs are retained but not counted).
* Period: 2010-12-01 to 2011-12-09; total quantity 5,176,450.
* Cancellation lines: 9,288 (3,836 distinct cancelled invoices); return lines: 10,624.
* Top product by quantity: 22197 SMALL POPCORN HOLDER (56,450 units).
* Top revenue country: United Kingdom (£8,187,806.36 signed).

## Notes

* Hive runs with an embedded Derby metastore on the local filesystem; the
  docker-compose setup intentionally avoids HDFS so no distributed execution is
  claimed.
* beeline may exit with code 1 due to a harmless `.beeline` config-directory
  warning; result sets are still emitted correctly.
* No machine learning is used; the strength of the project is genuine Hive-based
  processing and verified results.
