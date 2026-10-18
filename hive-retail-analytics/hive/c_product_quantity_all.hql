-- ============================================================================
-- c_product_quantity_all.hql
-- Product-level analysis: ALL products ranked by total quantity recorded.
--
-- StockCode is the product identifier; grouping is by StockCode so products
-- are never split or merged by description variance. The Description shown is
-- a representative label (the MAX non-null description); products with no
-- description at all are labelled '[missing description]'.
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
ORDER BY total_quantity DESC, StockCode;
