-- ============================================================================
-- 03_load_data.hql
--
-- Loads the preprocessed CSV into the staging table and the derived
-- category-rule mapping into product_categories.
--
-- Prerequisite (host, PowerShell):
--   docker cp data/processed/online_retail_clean.csv hive-server:/tmp/online_retail_clean.csv
--   docker cp config/category_rules.csv hive-server:/tmp/category_rules.csv
-- ============================================================================

USE retail_analytics;

-- Idempotent loads: truncate first so re-running does not duplicate data.
TRUNCATE TABLE raw_transactions;
TRUNCATE TABLE product_categories;

LOAD DATA LOCAL INPATH '/tmp/online_retail_clean.csv'
INTO TABLE raw_transactions;

LOAD DATA LOCAL INPATH '/tmp/category_rules.csv'
INTO TABLE product_categories;
