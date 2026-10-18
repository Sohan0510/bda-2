-- ============================================================================
-- g_daily_trend.hql
-- Daily sales trend (positive sales only).
-- ============================================================================

USE retail_analytics;

SELECT
  FROM_UNIXTIME(UNIX_TIMESTAMP(InvoiceDate), 'yyyy-MM-dd') AS transaction_date,
  COUNT(*) AS transaction_lines,
  COUNT(DISTINCT InvoiceNo) AS distinct_invoices,
  SUM(Quantity) AS quantity_sold,
  SUM(CASE WHEN Quantity > 0 AND NOT is_cancellation THEN line_amount ELSE 0 END) AS positive_sales_revenue_gbp
FROM transactions
GROUP BY FROM_UNIXTIME(UNIX_TIMESTAMP(InvoiceDate), 'yyyy-MM-dd')
ORDER BY transaction_date;
