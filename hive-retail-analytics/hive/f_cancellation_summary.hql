-- ============================================================================
-- f_cancellation_summary.hql
-- Cancellation analysis: invoice-level vs line-level counts.
--
-- Definitions:
--   * Cancellation: InvoiceNo begins with 'C' (invoice-level cancellation
--     signal). Counted both as distinct cancelled invoices and as lines.
--   * Cancellation counts are distinct from return-related lines.
-- ============================================================================

USE retail_analytics;

SELECT
  COUNT(DISTINCT CASE WHEN is_cancellation THEN InvoiceNo END) AS cancellation_invoices_distinct,
  SUM(CASE WHEN is_cancellation THEN 1 ELSE 0 END) AS cancellation_lines,
  COUNT(DISTINCT InvoiceNo) AS total_distinct_invoices,
  COUNT(*) AS total_lines
FROM transactions;
