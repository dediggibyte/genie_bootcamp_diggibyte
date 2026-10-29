-- ================================================================================================
-- BRONZE - domain sample `finance` (simplified). One streaming table per CSV folder: Auto Loader
-- (read_files) ingests every new file in /Volumes/${catalog}/landing/raw_files/<table>/ exactly once.
-- Every column stays STRING; _source_file and _ingested_at record the lineage.
-- ${catalog} is replaced by the pipeline configuration value `catalog` (resources/*.pipeline.yml).
-- ================================================================================================

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.company_code
COMMENT 'Bronze: raw finance.company_code rows exactly as delivered (all columns STRING).'
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '/Volumes/${catalog}/landing/raw_files/company_code/',
  format => 'csv',
  header => true,
  inferColumnTypes => false
);

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.gl_account
COMMENT 'Bronze: raw finance.gl_account rows exactly as delivered (all columns STRING).'
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '/Volumes/${catalog}/landing/raw_files/gl_account/',
  format => 'csv',
  header => true,
  inferColumnTypes => false
);

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.journal_entry_line
COMMENT 'Bronze: raw finance.journal_entry_line rows exactly as delivered (all columns STRING).'
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '/Volumes/${catalog}/landing/raw_files/journal_entry_line/',
  format => 'csv',
  header => true,
  inferColumnTypes => false
);

CREATE OR REFRESH STREAMING TABLE ${catalog}.bronze.ar_invoice
COMMENT 'Bronze: raw finance.ar_invoice rows exactly as delivered (all columns STRING).'
AS SELECT
  *,
  _metadata.file_path AS _source_file,
  current_timestamp() AS _ingested_at
FROM STREAM read_files(
  '/Volumes/${catalog}/landing/raw_files/ar_invoice/',
  format => 'csv',
  header => true,
  inferColumnTypes => false
);
