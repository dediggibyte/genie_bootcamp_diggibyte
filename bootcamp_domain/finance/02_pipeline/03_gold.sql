-- ================================================================================================
-- GOLD - domain sample `finance` (simplified): the 4 tables Genie and the business query.
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

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.finance.company_code (
  company_code STRING NOT NULL COMMENT 'Company code of the legal entity: SE01, NO01, DK01, FI01, DE01, PL01.',
  company_name STRING COMMENT 'Legal name, e.g. Fjällmark Deutschland GmbH.',
  country_code STRING COMMENT 'ISO 3166 alpha-3 country code.',
  currency_code STRING COMMENT 'Local (company code) currency: SEK, NOK, DKK, EUR, PLN.',
  eur_rate DECIMAL(10,4) COMMENT 'EUR per 1 unit of local currency (fixed rate of this sample).',
  is_parent BOOLEAN COMMENT 'TRUE for the group parent SE01.',
  CONSTRAINT pk_company_code PRIMARY KEY (company_code)
)
COMMENT 'The six legal entities (company codes) of Fjällmark with their local currency and the fixed EUR rate used in this sample.'
AS SELECT
  company_code,
  company_name,
  country_code,
  currency_code,
  eur_rate,
  is_parent
FROM ${catalog}.silver.company_code;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.finance.gl_account (
  gl_account_code STRING NOT NULL COMMENT 'GL account number, e.g. 3010.',
  account_name STRING COMMENT 'Account name, e.g. Sales revenue DTC webshop.',
  account_group STRING COMMENT 'P&L line: REVENUE (3010, 3020, 3090), COGS (4000, 4100) or OPEX (6000-6200).',
  CONSTRAINT pk_gl_account PRIMARY KEY (gl_account_code)
)
COMMENT 'Chart of accounts. account_group decides the P&L line of a posting.'
AS SELECT
  gl_account_code,
  account_name,
  account_group
FROM ${catalog}.silver.gl_account;

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.finance.journal_entry_line (
  journal_entry_line_id BIGINT NOT NULL COMMENT 'Unique id of the GL line.',
  posting_date DATE COMMENT 'Posting date (last day of the month).',
  fiscal_year INT COMMENT 'Fiscal year = calendar year.',
  fiscal_period INT COMMENT 'Fiscal period = month 1-12.',
  company_code STRING COMMENT 'Company code that booked the line (finance.company_code).',
  gl_account_code STRING COMMENT 'GL account (finance.gl_account).',
  brand STRING COMMENT 'Brand: Björkö Pantry, Kallkälla, Mjuk Care; NULL for OPEX.',
  channel STRING COMMENT 'Sales channel DTC (webshop) or B2B (trade); NULL for variances and OPEX.',
  currency_code STRING COMMENT 'Local currency of amount_local.',
  amount_local DECIMAL(18,2) COMMENT 'P&L amount in the local currency - never add across currencies.',
  amount_eur DECIMAL(18,2) COMMENT 'P&L amount in group currency EUR - use this across company codes.',
  CONSTRAINT pk_journal_entry_line PRIMARY KEY (journal_entry_line_id),
  CONSTRAINT fk_journal_entry_line_company_code FOREIGN KEY (company_code) REFERENCES ${catalog}.finance.company_code (company_code),
  CONSTRAINT fk_journal_entry_line_gl_account_code FOREIGN KEY (gl_account_code) REFERENCES ${catalog}.finance.gl_account (gl_account_code)
)
COMMENT 'General-ledger lines (monthly, posted) per company code, account, brand and channel. amount_eur is the P&L amount in EUR: revenue positive, returns and trade discounts negative, costs positive.'
AS SELECT
  journal_entry_line_id,
  posting_date,
  fiscal_year,
  fiscal_period,
  company_code,
  gl_account_code,
  brand,
  channel,
  currency_code,
  amount_local,
  amount_eur
FROM ${catalog}.silver.journal_entry_line
-- Build order only - never filters a row.
WHERE TRUE
   OR EXISTS (SELECT 1 FROM ${catalog}.finance.company_code)
   OR EXISTS (SELECT 1 FROM ${catalog}.finance.gl_account);

CREATE OR REFRESH MATERIALIZED VIEW ${catalog}.finance.ar_invoice (
  ar_invoice_id BIGINT NOT NULL COMMENT 'Unique id of the invoice.',
  invoice_number STRING COMMENT 'Invoice number, e.g. DE01-202606-001.',
  company_code STRING COMMENT 'Selling company code (finance.company_code).',
  customer_name STRING COMMENT 'B2B trade customer, e.g. Alpina Drogerie.',
  customer_contact_email STRING COMMENT 'E-mail of the customer\'s contact person - personal data, hidden from the Genie Agent.',
  billing_date DATE COMMENT 'Invoice date.',
  due_date DATE COMMENT 'Due date (30 days, 45 days for DE01).',
  payment_date DATE COMMENT 'Date the invoice was paid; NULL if still open.',
  currency_code STRING COMMENT 'Invoice currency = local currency of the company code.',
  total_amount_local DECIMAL(18,2) COMMENT 'Invoice amount in the invoice currency.',
  total_amount_eur DECIMAL(18,2) COMMENT 'Invoice amount in EUR.',
  outstanding_amount_local DECIMAL(18,2) COMMENT 'Open amount at 2026-09-30 in the invoice currency (0 when paid).',
  outstanding_amount_eur DECIMAL(18,2) COMMENT 'Open amount at 2026-09-30 in EUR (0 when paid).',
  invoice_status STRING COMMENT 'paid, open or disputed (customer disputes the invoice).',
  CONSTRAINT pk_ar_invoice PRIMARY KEY (ar_invoice_id),
  CONSTRAINT fk_ar_invoice_company_code FOREIGN KEY (company_code) REFERENCES ${catalog}.finance.company_code (company_code)
)
COMMENT 'B2B customer invoices (accounts receivable), status as of the reporting date 2026-09-30.'
AS SELECT
  ar_invoice_id,
  invoice_number,
  company_code,
  customer_name,
  customer_contact_email,
  billing_date,
  due_date,
  payment_date,
  currency_code,
  total_amount_local,
  total_amount_eur,
  outstanding_amount_local,
  outstanding_amount_eur,
  invoice_status
FROM ${catalog}.silver.ar_invoice
-- Build order only - never filters a row.
WHERE TRUE
   OR EXISTS (SELECT 1 FROM ${catalog}.finance.company_code);
