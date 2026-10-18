-- ============================================================================
-- c_product_top20_quantity.hql
-- Top 20 products by total quantity recorded (highest-demand products).
-- Grouped by StockCode; Description is a representative label.
-- ============================================================================

USE retail_analytics;

SELECT
  StockCode,
  COALESCE(MAX(CASE WHEN Description IS NOT NULL THEN Description END),
           '[missing description]') AS Description,
  SUM(Quantity) AS total_quantity,
  SUM(line_amount) AS total_sales_value_gbp,
  COUNT(DISTINCT InvoiceNo) AS distinct_invoices
FROM transactions
GROUP BY StockCode
ORDER BY total_quantity DESC, StockCode
LIMIT 20;
