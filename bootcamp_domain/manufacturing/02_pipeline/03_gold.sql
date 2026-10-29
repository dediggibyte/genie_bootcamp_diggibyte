-- ================================================================================================
-- GOLD - domain sample `manufacturing` (simplified): the 4 tables Genie and the business query.
-- Each materialized view carries the table and column comments (Genie reads them), a PRIMARY KEY and
-- 4 FOREIGN KEYs in total (informational constraints: Genie and BI tools derive their joins from them).
-- Gold reads silver only; row filters and column masks are attached to gold afterwards (notebook 03).
--
-- Build order: a FOREIGN KEY needs its referenced table first, but a pipeline only orders tables by the
-- data they read. So a query with a foreign key ends with
--     WHERE TRUE OR EXISTS (SELECT 1 FROM <referenced gold table>)
-- which never filters a row (TRUE OR ... is always true) but makes the pipeline build that table first.
-- Once notebook 03 has governed a referenced table, the pipeline recomputes the referring table on every
-- update instead of refreshing it incrementally: same rows, a few seconds at this data size.
-- Never use a full refresh: bronze ingests every file once.
-- ================================================================================================

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.manufacturing.plant (
  plant_code STRING NOT NULL COMMENT 'Plant code: SE-LUN, SE-NKP, FI-TMP, PL-POZ.',
  plant_name STRING COMMENT 'Plant name, e.g. Poznań Personal Care Plant.',
  country_code STRING COMMENT 'ISO 3166 alpha-3 country code.',
  company_code STRING COMMENT 'Company code that owns the plant.',
  main_brand STRING COMMENT 'Brand the plant produces.',
  commissioning_date DATE COMMENT 'Date the plant started production (FI-TMP: April 2025).',
  CONSTRAINT pk_plant PRIMARY KEY (plant_code)
)
COMMENT 'The four plants of Fjällmark.'
AS SELECT
  plant_code,
  plant_name,
  country_code,
  company_code,
  main_brand,
  commissioning_date
FROM ${catalog}.silver.plant;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.manufacturing.production_line (
  line_code STRING NOT NULL COMMENT 'Line code, e.g. PL-POZ-L2.',
  plant_code STRING COMMENT 'Plant of the line (manufacturing.plant).',
  line_name STRING COMMENT 'What the line does, e.g. Liquid filling (shampoo, body wash).',
  product_category STRING COMMENT 'FOOD, BEVERAGE or PERSONAL_CARE.',
  scrap_target_pct DECIMAL(5,1) COMMENT 'Target scrap rate in percent.',
  CONSTRAINT pk_production_line PRIMARY KEY (line_code),
  CONSTRAINT fk_production_line_plant_code FOREIGN KEY (plant_code) REFERENCES ${catalog}.manufacturing.plant (plant_code)
)
COMMENT 'Production lines, three per plant, named <plant>-L<n>.'
AS SELECT
  line_code,
  plant_code,
  line_name,
  product_category,
  scrap_target_pct
FROM ${catalog}.silver.production_line
-- Build order only - never filters a row.
WHERE TRUE
   OR EXISTS (SELECT 1 FROM ${catalog}.manufacturing.plant);

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.manufacturing.production_order (
  production_order_id BIGINT NOT NULL COMMENT 'Unique id of the production order.',
  order_number STRING COMMENT 'Production order number.',
  plant_code STRING COMMENT 'Plant (manufacturing.plant).',
  line_code STRING COMMENT 'Line (manufacturing.production_line).',
  product_name STRING COMMENT 'Product made.',
  brand STRING COMMENT 'Brand of the product.',
  planned_start_date DATE COMMENT 'Planned start.',
  planned_finish_date DATE COMMENT 'Planned finish (on time = actual_finish_date <= this).',
  actual_finish_date DATE COMMENT 'Actual finish; NULL if not completed.',
  order_status STRING COMMENT 'completed, in_progress or cancelled.',
  planned_qty INT COMMENT 'Planned quantity (units).',
  good_qty INT COMMENT 'Good units produced; NULL while in progress.',
  scrap_qty INT COMMENT 'Scrapped units; NULL while in progress.',
  planned_cost_eur DECIMAL(18,2) COMMENT 'Planned production cost, EUR.',
  actual_cost_eur DECIMAL(18,2) COMMENT 'Actual production cost, EUR - confidential, masked.',
  shift_supervisor STRING COMMENT 'Supervisor responsible - personal data, masked.',
  CONSTRAINT pk_production_order PRIMARY KEY (production_order_id),
  CONSTRAINT fk_production_order_plant_code FOREIGN KEY (plant_code) REFERENCES ${catalog}.manufacturing.plant (plant_code),
  CONSTRAINT fk_production_order_line_code FOREIGN KEY (line_code) REFERENCES ${catalog}.manufacturing.production_line (line_code)
)
COMMENT 'Production orders: one product on one line, with plan, actuals, quantities and cost. Only completed orders count for yield, scrap and on-time KPIs.'
AS SELECT
  production_order_id,
  order_number,
  plant_code,
  line_code,
  product_name,
  brand,
  planned_start_date,
  planned_finish_date,
  actual_finish_date,
  order_status,
  planned_qty,
  good_qty,
  scrap_qty,
  planned_cost_eur,
  actual_cost_eur,
  shift_supervisor
FROM ${catalog}.silver.production_order
-- Build order only - never filters a row.
WHERE TRUE
   OR EXISTS (SELECT 1 FROM ${catalog}.manufacturing.plant)
   OR EXISTS (SELECT 1 FROM ${catalog}.manufacturing.production_line);

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.manufacturing.downtime_event (
  downtime_event_id BIGINT NOT NULL COMMENT 'Unique id of the stop.',
  production_order_id BIGINT COMMENT 'Production order running at the time (manufacturing.production_order).',
  plant_code STRING COMMENT 'Plant of the line.',
  line_code STRING COMMENT 'Line that stopped.',
  event_date DATE COMMENT 'Date of the stop.',
  reason STRING COMMENT 'changeover, mechanical_failure, material_shortage, cleaning or quality_hold.',
  duration_min INT COMMENT 'Duration in minutes.',
  CONSTRAINT pk_downtime_event PRIMARY KEY (downtime_event_id),
  CONSTRAINT fk_downtime_event_production_order_id FOREIGN KEY (production_order_id) REFERENCES ${catalog}.manufacturing.production_order (production_order_id)
)
COMMENT 'Line stops during completed production orders, with reason and duration.'
AS SELECT
  downtime_event_id,
  production_order_id,
  plant_code,
  line_code,
  event_date,
  reason,
  duration_min
FROM ${catalog}.silver.downtime_event
-- Build order only - never filters a row.
WHERE TRUE
   OR EXISTS (SELECT 1 FROM ${catalog}.manufacturing.production_order);
