-- ============================================================================
-- e_country_summary.hql
-- Country-level analysis: revenue, quantity, transactions and identified
-- customers by country, ranked by revenue.
--
-- Describes observed transaction patterns only; no claims are made about
-- customer motivations.
-- ============================================================================

USE retail_analytics;

SELECT
  Country,
  COUNT(*) AS transaction_lines,
  COUNT(DISTINCT InvoiceNo) AS distinct_invoices,
  COUNT(DISTINCT CASE WHEN CustomerID IS NOT NULL THEN CustomerID END) AS identified_customers,
  SUM(Quantity) AS quantity_sold,
  SUM(line_amount) AS revenue_gbp
FROM transactions
GROUP BY Country
ORDER BY revenue_gbp DESC, Country;
