-- ============================================================================
-- e_country_monthly.hql
-- Country-wise monthly sales trends.
-- ============================================================================

USE retail_analytics;

SELECT
  Country,
  invoice_month AS month,
  COUNT(*) AS transaction_lines,
  COUNT(DISTINCT InvoiceNo) AS distinct_invoices,
  SUM(Quantity) AS quantity_sold,
  SUM(line_amount) AS revenue_gbp
FROM transactions
GROUP BY Country, invoice_month
ORDER BY Country, invoice_month;
