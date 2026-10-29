-- ================================================================================================
-- finance.receivables_metrics - open AR, overdue AR and DSO as of the reporting date 2026-09-30 (EUR).
-- Created by 01_notebooks/job_tasks/02a_create_metric_views.py. Definition: Page dso (05_context/pages/).
-- ================================================================================================
CREATE OR REPLACE VIEW ${catalog}.finance.`receivables_metrics`
WITH METRICS
LANGUAGE YAML
AS $$
  version: 1.1
  comment: >-
    B2B receivables KPIs as of 2026-09-30 at invoice grain, EUR: open AR, overdue AR, disputed AR,
    billed amount and DSO (open AR / (billed Jul-Sep 2026 / 92 days)), by company code, customer,
    invoice status, aging bucket and billing month.
  source: ${catalog}.finance.ar_invoice
  dimensions:
    - name: company_code
      expr: source.company_code
      display_name: Company code
      synonyms: [legal entity, entity, company]
    - name: customer_name
      expr: source.customer_name
      display_name: Customer
      synonyms: [customer, trade account]
    - name: invoice_status
      expr: source.invoice_status
      display_name: Invoice status
      comment: paid, open or disputed.
    - name: aging_bucket
      expr: >-
        CASE WHEN source.outstanding_amount_eur <= 0 THEN 'settled'
             WHEN source.due_date >= DATE'2026-09-30' THEN 'current'
             WHEN datediff(DATE'2026-09-30', source.due_date) <= 30 THEN '1-30 days'
             WHEN datediff(DATE'2026-09-30', source.due_date) <= 60 THEN '31-60 days'
             ELSE 'over 60 days' END
      display_name: Aging bucket
      comment: Days past due at 2026-09-30 of the open invoices; settled = nothing open.
      synonyms: [aging, AR aging]
    - name: billing_month
      expr: CAST(DATE_TRUNC('MONTH', source.billing_date) AS DATE)
      display_name: Billing month
  measures:
    - name: invoice_count
      expr: COUNT(source.ar_invoice_id)
      display_name: Invoices
      format:
        type: number
        decimal_places: {type: exact, places: 0}
    - name: open_ar_eur
      expr: SUM(source.outstanding_amount_eur)
      display_name: Open AR (EUR)
      comment: Open receivables at 2026-09-30, EUR.
      synonyms: [open AR, open receivables, outstanding balance]
      format:
        type: currency
        currency_code: EUR
        decimal_places: {type: exact, places: 2}
    - name: overdue_ar_eur
      expr: SUM(source.outstanding_amount_eur) FILTER (WHERE source.due_date < DATE'2026-09-30')
      display_name: Overdue AR (EUR)
      comment: Open amount of invoices past their due date at 2026-09-30, EUR.
      synonyms: [overdue receivables, past due]
      format:
        type: currency
        currency_code: EUR
        decimal_places: {type: exact, places: 2}
    - name: disputed_ar_eur
      expr: SUM(source.outstanding_amount_eur) FILTER (WHERE source.invoice_status = 'disputed')
      display_name: Disputed AR (EUR)
      synonyms: [disputes, disputed amount]
      format:
        type: currency
        currency_code: EUR
        decimal_places: {type: exact, places: 2}
    - name: billed_q3_2026_eur
      expr: SUM(source.total_amount_eur) FILTER (WHERE source.billing_date BETWEEN DATE'2026-07-01' AND DATE'2026-09-30')
      display_name: Billed Jul-Sep 2026 (EUR)
      comment: Credit sales of the last quarter, the denominator of DSO.
      format:
        type: currency
        currency_code: EUR
        decimal_places: {type: exact, places: 2}
    - name: dso_days
      expr: MEASURE(open_ar_eur) / (MEASURE(billed_q3_2026_eur) / 92)
      display_name: DSO (days)
      comment: Days sales outstanding at 2026-09-30 = open AR / (billed Jul-Sep 2026 / 92). Group by company code or customer, not by month.
      synonyms: [DSO, days sales outstanding, debtor days]
      format:
        type: number
        decimal_places: {type: exact, places: 1}
$$
