-- ============================================================================
-- 04_clean_transform.hql
--
-- Transforms the all-STRING staging table into the typed analytical table.
-- No records are deleted: cancellations, returns, missing values and
-- duplicates are preserved and flagged transparently.
--
-- Cleaning rules (documented):
--   * Description blank           -> NULL  (flagged is_missing_description)
--   * CustomerID blank            -> NULL  (flagged is_missing_customerid)
--   * InvoiceDate                 -> parsed to TIMESTAMP
--   * Quantity, UnitPrice, line_amount -> cast to numeric DECIMAL/INT
--   * is_cancellation             -> InvoiceNo begins with 'C' (cancelled order)
--   * is_return                   -> Quantity < 0 (returned line)
--   * is_duplicate                -> exact duplicate line (all key fields)
--   * invoice_month               -> YYYY-MM substring of InvoiceDate
-- ============================================================================

USE retail_analytics;

SET hive.exec.dynamic.partition.mode = nonstrict;

INSERT OVERWRITE TABLE transactions
SELECT
  InvoiceNo,
  StockCode,
  NULLIF(TRIM(Description), '') AS Description,
  CAST(Quantity AS INT) AS Quantity,
  CAST(InvoiceDate AS TIMESTAMP) AS InvoiceDate,
  CAST(UnitPrice AS DECIMAL(12,2)) AS UnitPrice,
  CAST(NULLIF(TRIM(CustomerID), '') AS BIGINT) AS CustomerID,
  Country,
  LOWER(is_cancellation) = 'true' AS is_cancellation,
  LOWER(is_return) = 'true' AS is_return,
  LOWER(is_missing_description) = 'true' AS is_missing_description,
  LOWER(is_missing_customerid) = 'true' AS is_missing_customerid,
  LOWER(is_duplicate) = 'true' AS is_duplicate,
  CAST(line_amount AS DECIMAL(18,2)) AS line_amount,
  SUBSTRING(InvoiceDate, 1, 7) AS invoice_month
FROM raw_transactions;
