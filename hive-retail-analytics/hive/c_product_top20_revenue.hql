-- ============================================================================
-- c_product_top20_revenue.hql
-- Top 20 products by total sales revenue (highest-value products).
--
-- Distinguishes products that sell many units from products that generate
-- higher revenue per unit. Grouped by StockCode.
-- ============================================================================

USE retail_analytics;

SELECT
  StockCode,
  COALESCE(MAX(CASE WHEN Description IS NOT NULL THEN Description END),
           '[missing description]') AS Description,
  SUM(line_amount) AS total_sales_value_gbp,
  SUM(Quantity) AS total_quantity,
  COUNT(DISTINCT InvoiceNo) AS distinct_invoices
FROM transactions
GROUP BY StockCode
ORDER BY total_sales_value_gbp DESC, StockCode
LIMIT 20;
