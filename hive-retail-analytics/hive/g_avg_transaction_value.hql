-- ============================================================================
-- g_avg_transaction_value.hql
-- Average transaction value per invoice (positive sales only).
-- ============================================================================

USE retail_analytics;

WITH invoice_values AS (
  SELECT InvoiceNo,
         SUM(CASE WHEN Quantity > 0 AND NOT is_cancellation THEN line_amount ELSE 0 END) AS invoice_value_gbp
  FROM transactions
  GROUP BY InvoiceNo
)
SELECT
  COUNT(*) AS distinct_invoices_with_positive_sales,
  ROUND(AVG(invoice_value_gbp), 2) AS avg_transaction_value_gbp,
  ROUND(MIN(invoice_value_gbp), 2) AS min_transaction_value_gbp,
  ROUND(MAX(invoice_value_gbp), 2) AS max_transaction_value_gbp
FROM invoice_values
WHERE invoice_value_gbp > 0;
