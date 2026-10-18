-- ============================================================================
-- g_hourly_pattern.hql
-- Hourly transaction pattern.
-- ============================================================================

USE retail_analytics;

SELECT
  hour(InvoiceDate) AS hour_of_day,
  COUNT(*) AS transaction_lines,
  COUNT(DISTINCT InvoiceNo) AS distinct_invoices,
  SUM(Quantity) AS quantity_sold,
  SUM(line_amount) AS signed_revenue_gbp
FROM transactions
GROUP BY hour(InvoiceDate)
ORDER BY hour_of_day;
