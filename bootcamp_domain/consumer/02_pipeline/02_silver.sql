-- ================================================================================================
-- SILVER - domain sample `consumer` (simplified). One materialized view per table:
--   * types: text trimmed (empty -> NULL), numbers and booleans with TRY_CAST, dates yyyy-MM-dd
--   * one row per primary key (the latest ingested row wins), rows without a key are dropped
-- ================================================================================================

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.consumer_silver.product (
  CONSTRAINT product_id_not_null EXPECT (product_id IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Silver: consumer.product typed and de-duplicated, one row per product_id.'
AS
WITH typed AS (
  SELECT
    NULLIF(trim(product_id), '') AS product_id,
    NULLIF(trim(product_name), '') AS product_name,
    NULLIF(trim(brand), '') AS brand,
    NULLIF(trim(category), '') AS category,
    TRY_CAST(NULLIF(trim(unit_price_eur), '') AS DECIMAL(18,2)) AS unit_price_eur,
    _ingested_at
  FROM ${catalog}.consumer_bronze.product
)
SELECT * EXCEPT (_ingested_at)
FROM typed
QUALIFY ROW_NUMBER() OVER (PARTITION BY product_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.consumer_silver.shopper (
  CONSTRAINT shopper_id_not_null EXPECT (shopper_id IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Silver: consumer.shopper typed and de-duplicated, one row per shopper_id.'
AS
WITH typed AS (
  SELECT
    TRY_CAST(NULLIF(trim(shopper_id), '') AS BIGINT) AS shopper_id,
    NULLIF(trim(given_name), '') AS given_name,
    NULLIF(trim(family_name), '') AS family_name,
    NULLIF(trim(email), '') AS email,
    NULLIF(trim(country_code), '') AS country_code,
    NULLIF(trim(company_code), '') AS company_code,
    NULLIF(trim(loyalty_tier), '') AS loyalty_tier,
    try_to_date(trim(signup_date), 'yyyy-MM-dd') AS signup_date,
    TRY_CAST(NULLIF(trim(marketing_opt_in), '') AS BOOLEAN) AS marketing_opt_in,
    _ingested_at
  FROM ${catalog}.consumer_bronze.shopper
)
SELECT * EXCEPT (_ingested_at)
FROM typed
QUALIFY ROW_NUMBER() OVER (PARTITION BY shopper_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.consumer_silver.dtc_order (
  CONSTRAINT order_id_not_null EXPECT (order_id IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Silver: consumer.dtc_order typed and de-duplicated, one row per order_id.'
AS
WITH typed AS (
  SELECT
    TRY_CAST(NULLIF(trim(order_id), '') AS BIGINT) AS order_id,
    NULLIF(trim(order_number), '') AS order_number,
    TRY_CAST(NULLIF(trim(shopper_id), '') AS BIGINT) AS shopper_id,
    NULLIF(trim(company_code), '') AS company_code,
    NULLIF(trim(country_code), '') AS country_code,
    try_to_date(trim(order_date), 'yyyy-MM-dd') AS order_date,
    NULLIF(trim(order_status), '') AS order_status,
    NULLIF(trim(currency_code), '') AS currency_code,
    TRY_CAST(NULLIF(trim(order_amount_local), '') AS DECIMAL(18,2)) AS order_amount_local,
    TRY_CAST(NULLIF(trim(order_amount_eur), '') AS DECIMAL(18,2)) AS order_amount_eur,
    TRY_CAST(NULLIF(trim(item_count), '') AS INT) AS item_count,
    _ingested_at
  FROM ${catalog}.consumer_bronze.dtc_order
)
SELECT * EXCEPT (_ingested_at)
FROM typed
QUALIFY ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.consumer_silver.dtc_order_line (
  CONSTRAINT order_line_id_not_null EXPECT (order_line_id IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Silver: consumer.dtc_order_line typed and de-duplicated, one row per order_line_id.'
AS
WITH typed AS (
  SELECT
    TRY_CAST(NULLIF(trim(order_line_id), '') AS BIGINT) AS order_line_id,
    TRY_CAST(NULLIF(trim(order_id), '') AS BIGINT) AS order_id,
    NULLIF(trim(company_code), '') AS company_code,
    NULLIF(trim(product_id), '') AS product_id,
    TRY_CAST(NULLIF(trim(quantity), '') AS INT) AS quantity,
    TRY_CAST(NULLIF(trim(unit_price_eur), '') AS DECIMAL(18,2)) AS unit_price_eur,
    TRY_CAST(NULLIF(trim(line_amount_eur), '') AS DECIMAL(18,2)) AS line_amount_eur,
    _ingested_at
  FROM ${catalog}.consumer_bronze.dtc_order_line
)
SELECT * EXCEPT (_ingested_at)
FROM typed
QUALIFY ROW_NUMBER() OVER (PARTITION BY order_line_id ORDER BY _ingested_at DESC) = 1;
