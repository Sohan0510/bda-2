-- ============================================================================
-- g_weekday_weekend.hql
-- Weekday versus weekend activity.
-- Hive dayofweek(): 1 = Sunday, 7 = Saturday.
-- ============================================================================

USE retail_analytics;

SELECT
  CASE WHEN dayofweek(InvoiceDate) IN (1, 7) THEN 'weekend' ELSE 'weekday' END AS day_type,
  COUNT(*) AS transaction_lines,
  COUNT(DISTINCT InvoiceNo) AS distinct_invoices,
  SUM(Quantity) AS quantity_sold,
  SUM(line_amount) AS signed_revenue_gbp,
  SUM(CASE WHEN Quantity > 0 AND NOT is_cancellation THEN line_amount ELSE 0 END) AS positive_sales_revenue_gbp
FROM transactions
GROUP BY CASE WHEN dayofweek(InvoiceDate) IN (1, 7) THEN 'weekend' ELSE 'weekday' END
ORDER BY day_type;
