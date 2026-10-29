-- ================================================================================================
-- SILVER - domain sample `manufacturing` (simplified). One materialized view per table:
--   * types: text trimmed (empty -> NULL), numbers and booleans with TRY_CAST, dates yyyy-MM-dd
--   * one row per primary key (the latest ingested row wins), rows without a key are dropped
-- ================================================================================================

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.silver.plant (
  CONSTRAINT plant_code_not_null EXPECT (plant_code IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Silver: manufacturing.plant typed and de-duplicated, one row per plant_code.'
AS
WITH typed AS (
  SELECT
    NULLIF(trim(plant_code), '') AS plant_code,
    NULLIF(trim(plant_name), '') AS plant_name,
    NULLIF(trim(country_code), '') AS country_code,
    NULLIF(trim(company_code), '') AS company_code,
    NULLIF(trim(main_brand), '') AS main_brand,
    try_to_date(trim(commissioning_date), 'yyyy-MM-dd') AS commissioning_date,
    _ingested_at
  FROM ${catalog}.bronze.plant
)
SELECT * EXCEPT (_ingested_at)
FROM typed
QUALIFY ROW_NUMBER() OVER (PARTITION BY plant_code ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.silver.production_line (
  CONSTRAINT line_code_not_null EXPECT (line_code IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Silver: manufacturing.production_line typed and de-duplicated, one row per line_code.'
AS
WITH typed AS (
  SELECT
    NULLIF(trim(line_code), '') AS line_code,
    NULLIF(trim(plant_code), '') AS plant_code,
    NULLIF(trim(line_name), '') AS line_name,
    NULLIF(trim(product_category), '') AS product_category,
    TRY_CAST(NULLIF(trim(scrap_target_pct), '') AS DECIMAL(5,1)) AS scrap_target_pct,
    _ingested_at
  FROM ${catalog}.bronze.production_line
)
SELECT * EXCEPT (_ingested_at)
FROM typed
QUALIFY ROW_NUMBER() OVER (PARTITION BY line_code ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.silver.production_order (
  CONSTRAINT production_order_id_not_null EXPECT (production_order_id IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Silver: manufacturing.production_order typed and de-duplicated, one row per production_order_id.'
AS
WITH typed AS (
  SELECT
    TRY_CAST(NULLIF(trim(production_order_id), '') AS BIGINT) AS production_order_id,
    NULLIF(trim(order_number), '') AS order_number,
    NULLIF(trim(plant_code), '') AS plant_code,
    NULLIF(trim(line_code), '') AS line_code,
    NULLIF(trim(product_name), '') AS product_name,
    NULLIF(trim(brand), '') AS brand,
    try_to_date(trim(planned_start_date), 'yyyy-MM-dd') AS planned_start_date,
    try_to_date(trim(planned_finish_date), 'yyyy-MM-dd') AS planned_finish_date,
    try_to_date(trim(actual_finish_date), 'yyyy-MM-dd') AS actual_finish_date,
    NULLIF(trim(order_status), '') AS order_status,
    TRY_CAST(NULLIF(trim(planned_qty), '') AS INT) AS planned_qty,
    TRY_CAST(NULLIF(trim(good_qty), '') AS INT) AS good_qty,
    TRY_CAST(NULLIF(trim(scrap_qty), '') AS INT) AS scrap_qty,
    TRY_CAST(NULLIF(trim(planned_cost_eur), '') AS DECIMAL(18,2)) AS planned_cost_eur,
    TRY_CAST(NULLIF(trim(actual_cost_eur), '') AS DECIMAL(18,2)) AS actual_cost_eur,
    NULLIF(trim(shift_supervisor), '') AS shift_supervisor,
    _ingested_at
  FROM ${catalog}.bronze.production_order
)
SELECT * EXCEPT (_ingested_at)
FROM typed
QUALIFY ROW_NUMBER() OVER (PARTITION BY production_order_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.silver.downtime_event (
  CONSTRAINT downtime_event_id_not_null EXPECT (downtime_event_id IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Silver: manufacturing.downtime_event typed and de-duplicated, one row per downtime_event_id.'
AS
WITH typed AS (
  SELECT
    TRY_CAST(NULLIF(trim(downtime_event_id), '') AS BIGINT) AS downtime_event_id,
    TRY_CAST(NULLIF(trim(production_order_id), '') AS BIGINT) AS production_order_id,
    NULLIF(trim(plant_code), '') AS plant_code,
    NULLIF(trim(line_code), '') AS line_code,
    try_to_date(trim(event_date), 'yyyy-MM-dd') AS event_date,
    NULLIF(trim(reason), '') AS reason,
    TRY_CAST(NULLIF(trim(duration_min), '') AS INT) AS duration_min,
    _ingested_at
  FROM ${catalog}.bronze.downtime_event
)
SELECT * EXCEPT (_ingested_at)
FROM typed
QUALIFY ROW_NUMBER() OVER (PARTITION BY downtime_event_id ORDER BY _ingested_at DESC) = 1;
