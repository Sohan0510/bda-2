-- ============================================================================
-- 02_create_tables.hql
--
-- Staging table: raw_transactions  (TEXTFILE, OpenCSVSerde, all columns STRING)
--   Holds the cleaned CSV exactly as produced by src/acquire_and_prepare.py.
--   No schema inference: every column is explicitly declared.
--
-- Analytical table: transactions (ORC, typed columns, derived flags,
--   line_amount and invoice_month pre-computed).
--
-- Monetary amounts use DECIMAL(12,2) / DECIMAL(18,2) to avoid binary
-- floating-point rounding errors.
-- ============================================================================

USE retail_analytics;

DROP TABLE IF EXISTS raw_transactions;
CREATE TABLE raw_transactions (
  InvoiceNo STRING,
  StockCode STRING,
  Description STRING,
  Quantity STRING,
  InvoiceDate STRING,
  UnitPrice STRING,
  CustomerID STRING,
  Country STRING,
  is_cancellation STRING,
  is_return STRING,
  is_missing_description STRING,
  is_missing_customerid STRING,
  is_duplicate STRING,
  line_amount STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
  "separatorChar" = ",",
  "quoteChar"     = '"',
  "escapeChar"    = "\\"
)
STORED AS TEXTFILE
TBLPROPERTIES ("skip.header.line.count" = "1");

DROP TABLE IF EXISTS transactions;
CREATE TABLE transactions (
  InvoiceNo STRING,
  StockCode STRING,
  Description STRING,
  Quantity INT,
  InvoiceDate TIMESTAMP,
  UnitPrice DECIMAL(12,2),
  CustomerID BIGINT,
  Country STRING,
  is_cancellation BOOLEAN,
  is_return BOOLEAN,
  is_missing_description BOOLEAN,
  is_missing_customerid BOOLEAN,
  is_duplicate BOOLEAN,
  line_amount DECIMAL(18,2),
  invoice_month STRING
)
STORED AS ORC;

-- Derived product-category mapping (documented, reproducible, separate from
-- query logic; loaded from config/category_rules.csv via 03_load_data.hql).
DROP TABLE IF EXISTS product_categories;
CREATE TABLE product_categories (
  keyword STRING,
  category STRING
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
  "separatorChar" = ",",
  "quoteChar"     = '"',
  "escapeChar"    = "\\"
)
STORED AS TEXTFILE
TBLPROPERTIES ("skip.header.line.count" = "1");
