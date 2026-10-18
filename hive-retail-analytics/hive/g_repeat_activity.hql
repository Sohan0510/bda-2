-- ============================================================================
-- g_repeat_activity.hql
-- Repeat-transaction activity among records with valid CustomerIDs.
-- ============================================================================

USE retail_analytics;

WITH customer_stats AS (
  SELECT CustomerID, COUNT(DISTINCT InvoiceNo) AS invoices_per_customer
  FROM transactions
  WHERE CustomerID IS NOT NULL
  GROUP BY CustomerID
)
SELECT
  (SELECT COUNT(DISTINCT CustomerID) FROM transactions WHERE CustomerID IS NOT NULL) AS identified_customers,
  (SELECT COUNT(DISTINCT InvoiceNo) FROM transactions WHERE CustomerID IS NOT NULL) AS distinct_invoices,
  (SELECT COUNT(*) FROM transactions) AS transaction_lines,
  ROUND(AVG(invoices_per_customer), 2) AS avg_invoices_per_customer,
  SUM(CASE WHEN invoices_per_customer > 1 THEN 1 ELSE 0 END) AS customers_with_repeat_invoices
FROM customer_stats;
