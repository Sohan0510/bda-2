-- ============================================================================
-- f_revenue_effect.hql
-- Monetary effect of cancellations and returns on sales totals.
-- ============================================================================

USE retail_analytics;

SELECT
  SUM(line_amount) AS gross_signed_value_gbp,
  SUM(CASE WHEN Quantity > 0 AND NOT is_cancellation THEN line_amount ELSE 0 END) AS positive_sales_value_gbp,
  SUM(CASE WHEN is_cancellation THEN line_amount ELSE 0 END) AS cancellation_lines_value_gbp,
  SUM(CASE WHEN Quantity < 0 THEN line_amount ELSE 0 END) AS negative_quantity_lines_value_gbp,
  SUM(line_amount) - SUM(CASE WHEN Quantity > 0 AND NOT is_cancellation THEN line_amount ELSE 0 END) AS adjustment_gbp
FROM transactions;
