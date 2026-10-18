-- ============================================================================
-- a_dataset_overview.hql
-- Dataset overview metrics (single result row).
--
-- Definitions:
--   * total_records            : every transaction line loaded (preserved)
--   * distinct_invoices        : distinct InvoiceNo values
--   * distinct_products        : distinct StockCode values
--   * distinct_countries       : distinct Country values
--   * identified_customers     : distinct CustomerID where CustomerID IS NOT NULL
--                                 (missing customer ids are NOT counted as customers)
--   * earliest/latest          : min/max InvoiceDate
--   * total_quantity_recorded  : sum of Quantity (signed, as recorded)
--   * cancellation_lines       : lines whose InvoiceNo begins with 'C'
--   * cancellation_invoices    : distinct cancelled invoices
--   * return_lines             : lines with Quantity < 0
-- ============================================================================

USE retail_analytics;

SELECT
  'dataset_overview' AS section,
  COUNT(*) AS total_records,
  COUNT(DISTINCT InvoiceNo) AS distinct_invoices,
  COUNT(DISTINCT StockCode) AS distinct_products,
  COUNT(DISTINCT Country) AS distinct_countries,
  COUNT(DISTINCT CASE WHEN CustomerID IS NOT NULL THEN CustomerID END) AS identified_customers,
  MIN(InvoiceDate) AS earliest_transaction_date,
  MAX(InvoiceDate) AS latest_transaction_date,
  SUM(Quantity) AS total_quantity_recorded,
  SUM(CASE WHEN is_cancellation THEN 1 ELSE 0 END) AS cancellation_lines,
  COUNT(DISTINCT CASE WHEN is_cancellation THEN InvoiceNo END) AS cancellation_invoices,
  SUM(CASE WHEN is_return THEN 1 ELSE 0 END) AS return_lines
FROM transactions;
