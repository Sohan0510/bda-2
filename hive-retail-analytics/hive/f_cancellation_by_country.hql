-- ============================================================================
-- f_cancellation_by_country.hql
-- Cancellation lines and value by country.
-- ============================================================================

USE retail_analytics;

SELECT
  Country,
  COUNT(DISTINCT CASE WHEN is_cancellation THEN InvoiceNo END) AS cancellation_invoices,
  SUM(CASE WHEN is_cancellation THEN 1 ELSE 0 END) AS cancellation_lines,
  SUM(CASE WHEN is_cancellation THEN line_amount ELSE 0 END) AS cancellation_value_gbp
FROM transactions
GROUP BY Country
ORDER BY cancellation_lines DESC, Country;
