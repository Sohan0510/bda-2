-- ============================================================================
-- g_customer_txn_distribution.hql
-- Distribution of identified customers' transaction (invoice) counts.
-- Only customers with a valid CustomerID are considered.
-- ============================================================================

USE retail_analytics;

WITH customer_invoice_counts AS (
  SELECT CustomerID, COUNT(DISTINCT InvoiceNo) AS invoice_count
  FROM transactions
  WHERE CustomerID IS NOT NULL
  GROUP BY CustomerID
),
banded AS (
  SELECT invoice_count,
         COUNT(DISTINCT CustomerID) AS identified_customers,
         SUM(invoice_count) AS total_invoices
  FROM customer_invoice_counts
  GROUP BY invoice_count
)
SELECT
  CASE
    WHEN invoice_count = 1 THEN '1 transaction'
    WHEN invoice_count BETWEEN 2 AND 5 THEN '2-5 transactions'
    WHEN invoice_count BETWEEN 6 AND 20 THEN '6-20 transactions'
    ELSE '20+ transactions'
  END AS transaction_count_band,
  SUM(identified_customers) AS identified_customers,
  SUM(total_invoices) AS total_invoices
FROM banded
GROUP BY
  CASE
    WHEN invoice_count = 1 THEN '1 transaction'
    WHEN invoice_count BETWEEN 2 AND 5 THEN '2-5 transactions'
    WHEN invoice_count BETWEEN 6 AND 20 THEN '6-20 transactions'
    ELSE '20+ transactions'
  END
ORDER BY MIN(invoice_count);
