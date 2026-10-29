-- ================================================================================================
-- finance.net_revenue_metrics - the OFFICIAL Net Revenue, COGS, gross margin and OPEX (EUR, general ledger).
-- Created by 01_notebooks/job_tasks/02a_create_metric_views.py (${catalog} = your catalog).
-- Definitions: Pages net_revenue and gross_margin (05_context/pages/).
-- ================================================================================================
CREATE OR REPLACE VIEW ${catalog}.finance.`net_revenue_metrics`
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: >-
    Official P&L KPIs of Fjällmark from the general ledger, in group currency EUR: Net Revenue (REVENUE
    accounts incl. returns and trade discounts), COGS, gross margin and OPEX, by fiscal year / quarter /
    period, company code, brand, channel and GL account.
  source: ${catalog}.finance.journal_entry_line
  joins:
    - name: account
      source: ${catalog}.finance.gl_account
      'on': source.gl_account_code = account.gl_account_code
    - name: company
      source: ${catalog}.finance.company_code
      'on': source.company_code = company.company_code
  dimensions:
    - name: fiscal_year
      expr: source.fiscal_year
      display_name: Fiscal year
      synonyms: [year]
    - name: fiscal_quarter
      expr: concat('Q', CAST(ceil(source.fiscal_period / 3) AS INT))
      display_name: Fiscal quarter
      comment: Q1 = periods 1-3 ... Q4 = periods 10-12.
      synonyms: [quarter]
    - name: fiscal_period
      expr: source.fiscal_period
      display_name: Fiscal period
      comment: Month 1-12.
      synonyms: [month, period]
    - name: posting_month
      expr: CAST(DATE_TRUNC('MONTH', source.posting_date) AS DATE)
      display_name: Posting month
    - name: company_code
      expr: source.company_code
      display_name: Company code
      synonyms: [legal entity, entity, company]
    - name: company_name
      expr: company.company_name
      display_name: Company name
    - name: brand
      expr: source.brand
      display_name: Brand
    - name: channel
      expr: source.channel
      display_name: Channel
      comment: DTC (webshop) or B2B (trade).
      synonyms: [sales channel]
    - name: account_group
      expr: account.account_group
      display_name: Account group
      comment: REVENUE, COGS or OPEX.
    - name: gl_account
      expr: concat(source.gl_account_code, ' ', account.account_name)
      display_name: GL account
  measures:
    - name: net_revenue_eur
      expr: SUM(source.amount_eur) FILTER (WHERE account.account_group = 'REVENUE')
      display_name: Net revenue (EUR)
      comment: Revenue accounts 3010 + 3020 + 3090 (returns and trade discounts are negative), EUR.
      synonyms: [revenue, net revenue, sales, net sales, turnover]
      format:
        type: currency
        currency_code: EUR
        decimal_places: {type: exact, places: 2}
    - name: cogs_eur
      expr: SUM(source.amount_eur) FILTER (WHERE account.account_group = 'COGS')
      display_name: COGS (EUR)
      comment: Cost of goods sold = standard cost (4000) + production variances (4100), EUR.
      synonyms: [cost of goods sold, cost of sales]
      format:
        type: currency
        currency_code: EUR
        decimal_places: {type: exact, places: 2}
    - name: gross_margin_eur
      expr: MEASURE(net_revenue_eur) - MEASURE(cogs_eur)
      display_name: Gross margin (EUR)
      synonyms: [gross profit]
      format:
        type: currency
        currency_code: EUR
        decimal_places: {type: exact, places: 2}
    - name: gross_margin_pct
      expr: 100 * (MEASURE(net_revenue_eur) - MEASURE(cogs_eur)) / MEASURE(net_revenue_eur)
      display_name: Gross margin %
      comment: Gross margin / net revenue in percent - a ratio of sums.
      synonyms: [GM%, margin %]
      format:
        type: number
        decimal_places: {type: exact, places: 1}
    - name: opex_eur
      expr: SUM(source.amount_eur) FILTER (WHERE account.account_group = 'OPEX')
      display_name: OPEX (EUR)
      comment: Operating expenses (marketing, personnel, freight), EUR.
      synonyms: [operating expenses]
      format:
        type: currency
        currency_code: EUR
        decimal_places: {type: exact, places: 2}
$$
