-- ============================================================================
-- c_product_low_volume.hql
-- Products with relatively low transaction volumes (<= 5 transaction lines).
-- Grouped by StockCode.
-- ============================================================================

USE retail_analytics;

SELECT
  StockCode,
  COALESCE(MAX(CASE WHEN Description IS NOT NULL THEN Description END),
           '[missing description]') AS Description,
  SUM(Quantity) AS total_quantity,
  SUM(line_amount) AS total_sales_value_gbp,
  COUNT(DISTINCT InvoiceNo) AS distinct_invoices,
  COUNT(*) AS transaction_lines
FROM transactions
GROUP BY StockCode
HAVING COUNT(*) <= 5
ORDER BY transaction_lines ASC, total_quantity ASC;
