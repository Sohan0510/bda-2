-- ============================================================================
-- f_quantity_direction.hql
-- Positive versus negative quantity lines and their monetary values.
--
-- Cancellation and return flags are independent (a cancelled invoice may
-- contain positive- or negative-quantity lines), so each line is classified
-- into exactly one bucket to avoid double counting:
--   * cancellation         : InvoiceNo begins with 'C'
--   * return_negative_qty  : Quantity < 0 and not a cancellation line
--   * positive_sale        : Quantity > 0 and not a cancellation line
-- ============================================================================

USE retail_analytics;

SELECT
  CASE
    WHEN is_cancellation THEN 'cancellation'
    WHEN Quantity < 0 THEN 'return_negative_quantity'
    ELSE 'positive_sale'
  END AS line_type,
  COUNT(*) AS lines,
  SUM(Quantity) AS total_quantity,
  SUM(line_amount) AS total_value_gbp,
  COUNT(DISTINCT InvoiceNo) AS distinct_invoices
FROM transactions
GROUP BY
  CASE
    WHEN is_cancellation THEN 'cancellation'
    WHEN Quantity < 0 THEN 'return_negative_quantity'
    ELSE 'positive_sale'
  END
ORDER BY lines DESC;
