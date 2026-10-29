-- ================================================================================================
-- BRONZE - domain sample `manufacturing` (simplified). One streaming table per CSV folder: Auto Loader
-- (read_files) ingests every new file in /Volumes/${catalog}/landing/raw_files/<table>/ exactly once.
-- Every column stays STRING; _source_file and _ingested_at record the lineage.
-- ${catalog} is replaced by the pipeline configuration value `catalog` (resources/*.pipeline.yml).
-- ================================================================================================

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.plant
COMMENT 'Bronze: raw manufacturing.plant rows exactly as delivered (all columns STRING).'
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '/Volumes/${catalog}/landing/raw_files/plant/',
  format => 'csv',
  header => true,
  inferColumnTypes => false
);

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.production_line
COMMENT 'Bronze: raw manufacturing.production_line rows exactly as delivered (all columns STRING).'
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '/Volumes/${catalog}/landing/raw_files/production_line/',
  format => 'csv',
  header => true,
  inferColumnTypes => false
);

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.production_order
COMMENT 'Bronze: raw manufacturing.production_order rows exactly as delivered (all columns STRING).'
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '/Volumes/${catalog}/landing/raw_files/production_order/',
  format => 'csv',
  header => true,
  inferColumnTypes => false
);

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.downtime_event
COMMENT 'Bronze: raw manufacturing.downtime_event rows exactly as delivered (all columns STRING).'
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '/Volumes/${catalog}/landing/raw_files/downtime_event/',
  format => 'csv',
  header => true,
  inferColumnTypes => false
);
