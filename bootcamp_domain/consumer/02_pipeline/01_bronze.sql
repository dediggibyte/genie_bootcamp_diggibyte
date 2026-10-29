-- ================================================================================================
-- BRONZE - domain sample `consumer` (simplified). One streaming table per CSV folder: Auto Loader
-- (read_files) ingests every new file in /Volumes/${catalog}/landing/raw_files/<table>/ exactly once.
-- Every column stays STRING; _source_file and _ingested_at record the lineage.
-- ${catalog} is replaced by the pipeline configuration value `catalog` (resources/*.pipeline.yml).
-- ================================================================================================

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.product
COMMENT 'Bronze: raw consumer.product rows exactly as delivered (all columns STRING).'
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '/Volumes/${catalog}/landing/raw_files/product/',
  format => 'csv',
  header => true,
  inferColumnTypes => false
);

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.shopper
COMMENT 'Bronze: raw consumer.shopper rows exactly as delivered (all columns STRING).'
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '/Volumes/${catalog}/landing/raw_files/shopper/',
  format => 'csv',
  header => true,
  inferColumnTypes => false
);

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.dtc_order
COMMENT 'Bronze: raw consumer.dtc_order rows exactly as delivered (all columns STRING).'
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '/Volumes/${catalog}/landing/raw_files/dtc_order/',
  format => 'csv',
  header => true,
  inferColumnTypes => false
);

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.dtc_order_line
COMMENT 'Bronze: raw consumer.dtc_order_line rows exactly as delivered (all columns STRING).'
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '/Volumes/${catalog}/landing/raw_files/dtc_order_line/',
  format => 'csv',
  header => true,
  inferColumnTypes => false
);
