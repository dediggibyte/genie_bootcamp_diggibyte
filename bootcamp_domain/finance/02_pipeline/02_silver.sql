-- ================================================================================================
-- SILVER - domain sample `finance` (simplified). One materialized view per table:
--   * types: text trimmed (empty -> NULL), numbers and booleans with TRY_CAST, dates yyyy-MM-dd
--   * one row per primary key (the latest ingested row wins), rows without a key are dropped
-- ================================================================================================

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.finance_silver.company_code (
  CONSTRAINT company_code_not_null EXPECT (company_code IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Silver: finance.company_code typed and de-duplicated, one row per company_code.'
AS
WITH typed AS (
  SELECT
    NULLIF(trim(company_code), '') AS company_code,
    NULLIF(trim(company_name), '') AS company_name,
    NULLIF(trim(country_code), '') AS country_code,
    NULLIF(trim(currency_code), '') AS currency_code,
    TRY_CAST(NULLIF(trim(eur_rate), '') AS DECIMAL(10,4)) AS eur_rate,
    TRY_CAST(NULLIF(trim(is_parent), '') AS BOOLEAN) AS is_parent,
    _ingested_at
  FROM ${catalog}.finance_bronze.company_code
)
SELECT * EXCEPT (_ingested_at)
FROM typed
QUALIFY ROW_NUMBER() OVER (PARTITION BY company_code ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.finance_silver.gl_account (
  CONSTRAINT gl_account_code_not_null EXPECT (gl_account_code IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Silver: finance.gl_account typed and de-duplicated, one row per gl_account_code.'
AS
WITH typed AS (
  SELECT
    NULLIF(trim(gl_account_code), '') AS gl_account_code,
    NULLIF(trim(account_name), '') AS account_name,
    NULLIF(trim(account_group), '') AS account_group,
    _ingested_at
  FROM ${catalog}.finance_bronze.gl_account
)
SELECT * EXCEPT (_ingested_at)
FROM typed
QUALIFY ROW_NUMBER() OVER (PARTITION BY gl_account_code ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.finance_silver.journal_entry_line (
  CONSTRAINT journal_entry_line_id_not_null EXPECT (journal_entry_line_id IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Silver: finance.journal_entry_line typed and de-duplicated, one row per journal_entry_line_id.'
AS
WITH typed AS (
  SELECT
    TRY_CAST(NULLIF(trim(journal_entry_line_id), '') AS BIGINT) AS journal_entry_line_id,
    try_to_date(trim(posting_date), 'yyyy-MM-dd') AS posting_date,
    TRY_CAST(NULLIF(trim(fiscal_year), '') AS INT) AS fiscal_year,
    TRY_CAST(NULLIF(trim(fiscal_period), '') AS INT) AS fiscal_period,
    NULLIF(trim(company_code), '') AS company_code,
    NULLIF(trim(gl_account_code), '') AS gl_account_code,
    NULLIF(trim(brand), '') AS brand,
    NULLIF(trim(channel), '') AS channel,
    NULLIF(trim(currency_code), '') AS currency_code,
    TRY_CAST(NULLIF(trim(amount_local), '') AS DECIMAL(18,2)) AS amount_local,
    TRY_CAST(NULLIF(trim(amount_eur), '') AS DECIMAL(18,2)) AS amount_eur,
    _ingested_at
  FROM ${catalog}.finance_bronze.journal_entry_line
)
SELECT * EXCEPT (_ingested_at)
FROM typed
QUALIFY ROW_NUMBER() OVER (PARTITION BY journal_entry_line_id ORDER BY _ingested_at DESC) = 1;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.finance_silver.ar_invoice (
  CONSTRAINT ar_invoice_id_not_null EXPECT (ar_invoice_id IS NOT NULL) ON VIOLATION DROP ROW
)
COMMENT 'Silver: finance.ar_invoice typed and de-duplicated, one row per ar_invoice_id.'
AS
WITH typed AS (
  SELECT
    TRY_CAST(NULLIF(trim(ar_invoice_id), '') AS BIGINT) AS ar_invoice_id,
    NULLIF(trim(invoice_number), '') AS invoice_number,
    NULLIF(trim(company_code), '') AS company_code,
    NULLIF(trim(customer_name), '') AS customer_name,
    NULLIF(trim(customer_contact_email), '') AS customer_contact_email,
    try_to_date(trim(billing_date), 'yyyy-MM-dd') AS billing_date,
    try_to_date(trim(due_date), 'yyyy-MM-dd') AS due_date,
    try_to_date(trim(payment_date), 'yyyy-MM-dd') AS payment_date,
    NULLIF(trim(currency_code), '') AS currency_code,
    TRY_CAST(NULLIF(trim(total_amount_local), '') AS DECIMAL(18,2)) AS total_amount_local,
    TRY_CAST(NULLIF(trim(total_amount_eur), '') AS DECIMAL(18,2)) AS total_amount_eur,
    TRY_CAST(NULLIF(trim(outstanding_amount_local), '') AS DECIMAL(18,2)) AS outstanding_amount_local,
    TRY_CAST(NULLIF(trim(outstanding_amount_eur), '') AS DECIMAL(18,2)) AS outstanding_amount_eur,
    NULLIF(trim(invoice_status), '') AS invoice_status,
    _ingested_at
  FROM ${catalog}.finance_bronze.ar_invoice
)
SELECT * EXCEPT (_ingested_at)
FROM typed
QUALIFY ROW_NUMBER() OVER (PARTITION BY ar_invoice_id ORDER BY _ingested_at DESC) = 1;
