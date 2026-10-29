-- ================================================================================================
-- GOLD - domain sample `consumer` (simplified): the 4 tables Genie and the business query.
-- Each materialized view carries the table and column comments (Genie reads them), a PRIMARY KEY and
-- 3 FOREIGN KEYs in total (informational constraints: Genie and BI tools derive their joins from them).
-- Gold reads silver only; the row filter is attached to gold afterwards (notebook 03).
--
-- Build order: a FOREIGN KEY needs its referenced table first, but a pipeline only orders tables by the
-- data they read. So a query with a foreign key ends with
--     WHERE TRUE OR EXISTS (SELECT 1 FROM <referenced gold table>)
-- which never filters a row (TRUE OR ... is always true) but makes the pipeline build that table first.
-- Once notebook 03 has governed a referenced table, the pipeline recomputes the referring table on every
-- update instead of refreshing it incrementally: same rows, a few seconds at this data size.
-- Never use a full refresh: bronze ingests every file once.
-- ================================================================================================

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.consumer.product (
  product_id STRING NOT NULL COMMENT 'Product id, e.g. KK-LEMON.',
  product_name STRING COMMENT 'Product name.',
  brand STRING COMMENT 'Brand: Björkö Pantry, Kallkälla, Mjuk Care.',
  category STRING COMMENT 'FOOD, BEVERAGE or PERSONAL_CARE.',
  unit_price_eur DECIMAL(18,2) COMMENT 'List price per unit in EUR, net of VAT.',
  CONSTRAINT pk_product PRIMARY KEY (product_id)
)
COMMENT 'The 12 products sold in the webshop, with brand, category and list price.'
AS SELECT
  product_id,
  product_name,
  brand,
  category,
  unit_price_eur
FROM ${catalog}.consumer_silver.product;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.consumer.shopper (
  shopper_id BIGINT NOT NULL COMMENT 'Unique id of the shopper.',
  given_name STRING COMMENT 'Given name - personal data.',
  family_name STRING COMMENT 'Family name - personal data.',
  email STRING COMMENT 'E-mail address - personal data.',
  country_code STRING COMMENT 'Market country: SWE, NOR, DNK, FIN, DEU, NLD.',
  company_code STRING COMMENT 'Selling entity of the market: SE01, NO01, DK01, FI01, DE01 (Germany and the Netherlands).',
  loyalty_tier STRING COMMENT 'Fjällmark Friends tier: Bronze, Silver, Gold, Platinum; NULL = not a member.',
  signup_date DATE COMMENT 'Date the shopper registered.',
  marketing_opt_in BOOLEAN COMMENT 'TRUE if the shopper agreed to marketing e-mails.',
  CONSTRAINT pk_shopper PRIMARY KEY (shopper_id)
)
COMMENT 'Registered webshop shoppers with market and loyalty tier. Names and e-mail are personal data.'
AS SELECT
  shopper_id,
  given_name,
  family_name,
  email,
  country_code,
  company_code,
  loyalty_tier,
  signup_date,
  marketing_opt_in
FROM ${catalog}.consumer_silver.shopper;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.consumer.dtc_order (
  order_id BIGINT NOT NULL COMMENT 'Unique id of the order.',
  order_number STRING COMMENT 'Order number shown to the shopper.',
  shopper_id BIGINT COMMENT 'Shopper who placed the order (consumer.shopper).',
  company_code STRING COMMENT 'Selling entity of the market.',
  country_code STRING COMMENT 'Market country: SWE, NOR, DNK, FIN, DEU, NLD.',
  order_date DATE COMMENT 'Date the order was placed.',
  order_status STRING COMMENT 'delivered, returned or cancelled. Cancelled orders never count in GMV.',
  currency_code STRING COMMENT 'Market currency of order_amount_local.',
  order_amount_local DECIMAL(18,2) COMMENT 'Order value in the market currency.',
  order_amount_eur DECIMAL(18,2) COMMENT 'Order value in EUR - use this across markets.',
  item_count INT COMMENT 'Number of units in the order.',
  CONSTRAINT pk_dtc_order PRIMARY KEY (order_id),
  CONSTRAINT fk_dtc_order_shopper_id FOREIGN KEY (shopper_id) REFERENCES ${catalog}.consumer.shopper (shopper_id)
)
COMMENT 'Webshop (DTC) orders, one row per order. Amounts are net of VAT and excl. shipping.'
AS SELECT
  order_id,
  order_number,
  shopper_id,
  company_code,
  country_code,
  order_date,
  order_status,
  currency_code,
  order_amount_local,
  order_amount_eur,
  item_count
FROM ${catalog}.consumer_silver.dtc_order
-- Build order only - never filters a row.
WHERE TRUE
   OR EXISTS (SELECT 1 FROM ${catalog}.consumer.shopper);

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.consumer.dtc_order_line (
  order_line_id BIGINT NOT NULL COMMENT 'Unique id of the order line.',
  order_id BIGINT COMMENT 'Order of the line (consumer.dtc_order).',
  company_code STRING COMMENT 'Selling entity (same as the order; drives the row filter).',
  product_id STRING COMMENT 'Product (consumer.product).',
  quantity INT COMMENT 'Units ordered.',
  unit_price_eur DECIMAL(18,2) COMMENT 'Price per unit in EUR.',
  line_amount_eur DECIMAL(18,2) COMMENT 'quantity x unit_price_eur, EUR.',
  CONSTRAINT pk_dtc_order_line PRIMARY KEY (order_line_id),
  CONSTRAINT fk_dtc_order_line_order_id FOREIGN KEY (order_id) REFERENCES ${catalog}.consumer.dtc_order (order_id),
  CONSTRAINT fk_dtc_order_line_product_id FOREIGN KEY (product_id) REFERENCES ${catalog}.consumer.product (product_id)
)
COMMENT 'Webshop order lines: one product per line, with quantity and amount in EUR.'
AS SELECT
  order_line_id,
  order_id,
  company_code,
  product_id,
  quantity,
  unit_price_eur,
  line_amount_eur
FROM ${catalog}.consumer_silver.dtc_order_line
-- Build order only - never filters a row.
WHERE TRUE
   OR EXISTS (SELECT 1 FROM ${catalog}.consumer.dtc_order)
   OR EXISTS (SELECT 1 FROM ${catalog}.consumer.product);
