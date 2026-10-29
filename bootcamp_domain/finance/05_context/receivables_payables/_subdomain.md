---
title: Receivables Payables
domain: Finance
subdomain: Receivables Payables
subdomain_tag: Finance/Receivables Payables
description: Money customers owe the group. B2B customer invoices with billing and due dates, payments and the open amount as of 30 September 2026, in local currency and EUR. DSO and overdue receivables are calculated here.
tables: ar_invoice
metric_views: receivables_metrics
---

# Receivables Payables (Finance)

B2B trade receivables: every customer invoice since January 2025 and its status at the reporting date
**2026-09-30**. (The simplified sample has no payables.)

| Table | Primary key | What it holds |
|---|---|---|
| `ar_invoice` | `ar_invoice_id` | invoice, customer, billing / due / payment date, total and open amount (local and EUR), status `paid`, `open` or `disputed` |

Join: `ar_invoice.company_code` → `finance.company_code`. Metric view: `<catalog>.finance.receivables_metrics`.
Payment terms are 30 days (45 days for DE01). `customer_contact_email` is personal data and masked.

## Questions this sub-domain answers

* What is DSO by company code?
* How much is overdue, and with which customers?
* Why is DE01's DSO so much higher than the group's?

Page: [DSO](../pages/dso.md).
