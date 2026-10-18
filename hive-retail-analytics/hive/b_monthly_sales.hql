-- ============================================================================
-- b_monthly_sales.hql
-- Monthly sales analysis.
--
-- Cancellation/return handling:
--   * signed_revenue_gbp           : sum of line_amount over ALL lines
--                                    (cancellations/returns reduce the total)
--   * positive_sales_revenue_gbp   : sum of line_amount over lines with
--                                    Quantity > 0 AND NOT cancellation only
--   * cancellation_adjustment_gbp  : sum of line_amount over cancellation lines
--   * quantity_sold / positive_sales_quantity : signed vs positive-only
--
-- Revenue is displayed in GBP. Positive-sales totals are NOT labelled net
-- revenue unless cancellations/returns are netted off (signed_revenue_gbp).
-- ============================================================================

USE retail_analytics;

SELECT
  invoice_month AS month,
  COUNT(*) AS transaction_lines,
  COUNT(DISTINCT InvoiceNo) AS distinct_invoices,
  SUM(Quantity) AS quantity_sold,
  SUM(CASE WHEN Quantity > 0 AND NOT is_cancellation THEN Quantity ELSE 0 END) AS positive_sales_quantity,
  SUM(line_amount) AS signed_revenue_gbp,
  SUM(CASE WHEN Quantity > 0 AND NOT is_cancellation THEN line_amount ELSE 0 END) AS positive_sales_revenue_gbp,
  SUM(CASE WHEN is_cancellation THEN line_amount ELSE 0 END) AS cancellation_adjustment_gbp,
  ROUND(AVG(CASE WHEN Quantity > 0 AND NOT is_cancellation THEN line_amount END), 2) AS avg_positive_line_value_gbp
FROM transactions
GROUP BY invoice_month
ORDER BY invoice_month;
