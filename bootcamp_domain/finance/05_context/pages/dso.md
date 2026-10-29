---
title: DSO (Days Sales Outstanding)
domain: Finance
subdomain: Receivables Payables
synonyms: [DSO, days sales outstanding, debtor days, collection period, kundfordringsdagar]
description: "How many days of credit sales are tied up in open receivables: open AR at 2026-09-30 ÷ (credit sales billed in Q3 2026 ÷ 92 days), per company code."
owner: Group Credit Manager (role)
related_assets: [<catalog>.finance.receivables_metrics, <catalog>.finance.ar_invoice, <catalog>.finance.company_code]
sources: [Fjällmark Credit & Collections Policy, section 4 (fictional)]
---

# DSO - Days Sales Outstanding

## Definition

> **DSO** = open receivables at the reporting date ÷ (credit sales billed in the last quarter ÷ days in the quarter)

* **Open receivables** = Σ `ar_invoice.outstanding_amount_eur` (0 for paid invoices).
* **Credit sales** = Σ `ar_invoice.total_amount_eur` of invoices with `billing_date` in July-September 2026.
* **Reporting date** = 2026-09-30, so the quarter has **92 days**.

Reference values: **group ≈ 43 days**, **DE01 ≈ 72 days**; the other company codes are between 28 and 41 days.
Payment terms are 30 days (45 days in DE01), so a DSO near the terms is healthy.

## Business rules

1. Calculate DSO per company code (or for the group by adding both components first, then dividing).
2. Disputed invoices stay **in** DSO - they are unpaid - but are reported separately (`disputed_ar_eur`).
3. Overdue = open amount with `due_date` before 2026-09-30.

## How to calculate (SQL)

```sql
SELECT company_code, MEASURE(open_ar_eur) AS open_ar_eur, MEASURE(dso_days) AS dso_days
FROM <catalog>.finance.receivables_metrics
GROUP BY ALL ORDER BY dso_days DESC;
```

## Known event

Since **June 2026** the German drugstore customer **Alpina Drogerie** disputes its invoices with DE01. They are
unpaid, so DE01's DSO is far above the group's.

## Pitfalls

| Wrong answer | Why |
|---|---|
| `AVG(datediff(payment_date, billing_date))` | Average days to pay of *paid* invoices; ignores what is still open |
| Averaging the company-code DSOs | Unweighted; divide the sums instead |
| Grouping DSO by billing month | DSO is a point-in-time ratio at 2026-09-30 |

## Example questions

* What is DSO by company code?
* Why is DSO in Germany so much higher than in the rest of the group?
