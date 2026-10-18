-- ============================================================================
-- d_category_analysis.hql
-- Category-level analysis on a DERIVED (not official) classification.
--
-- The source dataset provides no product-category column, so categories are
-- derived from transparent keyword rules stored separately in
-- config/category_rules.csv and loaded into product_categories.
--
-- Rules (documented, reproducible):
--   * A product matches the rule whose keyword appears (case-insensitive,
--     whole-word) in its Description; the longest keyword wins.
--   * Products matching no rule, or with a missing description, are assigned
--     to the explicit 'Unclassified' category.
--   * Original StockCode and Description are preserved. Categories are
--     derived rather than supplied by the dataset.
-- ============================================================================

USE retail_analytics;

-- Candidate matches: each distinct product x category whose keyword appears
-- in the product description (case-insensitive whole-word match).
CREATE TEMPORARY TABLE category_matches AS
SELECT
  p.StockCode,
  p.Description,
  pc.category,
  LENGTH(pc.keyword) AS kw_len
FROM (
  SELECT DISTINCT StockCode, Description
  FROM transactions
) p
JOIN product_categories pc
  ON LOWER(COALESCE(p.Description, '')) RLIKE
     CONCAT('(^|[^A-Za-z0-9])', LOWER(pc.keyword), '([^A-Za-z0-9]|$)');

-- Keep the single best (longest keyword) match per product.
CREATE TEMPORARY TABLE product_category_assigned AS
SELECT StockCode, category
FROM (
  SELECT StockCode, category,
         ROW_NUMBER() OVER (PARTITION BY StockCode ORDER BY kw_len DESC, category ASC) AS rn
  FROM category_matches
) ranked
WHERE rn = 1;

-- Products with no matching rule (incl. missing description) -> Unclassified.
CREATE TEMPORARY TABLE product_category_unclassified AS
SELECT p.StockCode, 'Unclassified' AS category
FROM (SELECT DISTINCT StockCode FROM transactions) p
LEFT JOIN product_category_assigned a ON p.StockCode = a.StockCode
WHERE a.StockCode IS NULL;

-- Complete assignment: matched products + unclassified products.
CREATE TEMPORARY TABLE product_category_assign AS
SELECT * FROM product_category_assigned
UNION ALL
SELECT * FROM product_category_unclassified;

-- Category-level quantities and revenue.
SELECT
  pca.category AS product_category,
  COUNT(DISTINCT t.StockCode) AS distinct_products,
  SUM(t.Quantity) AS total_quantity_sold,
  SUM(t.line_amount) AS total_revenue_gbp,
  COUNT(*) AS transaction_lines,
  COUNT(DISTINCT t.InvoiceNo) AS distinct_invoices
FROM transactions t
JOIN product_category_assign pca ON t.StockCode = pca.StockCode
GROUP BY pca.category
ORDER BY total_revenue_gbp DESC;
