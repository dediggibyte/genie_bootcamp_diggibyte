---
title: Net Revenue
domain: Finance
subdomain: General Ledger
synonyms: [revenue, net sales, sales, turnover, nettoomsättning]
description: "The official revenue of Fjällmark: the sum of the general-ledger revenue accounts 3010 (DTC), 3020 (B2B) and 3090 (returns and trade discounts, negative) in group currency EUR."
owner: Group Financial Controller (role)
related_assets: [<catalog>.finance.net_revenue_metrics, <catalog>.finance.journal_entry_line, <catalog>.finance.gl_account, <catalog>.finance.company_code]
sources: [Fjällmark Group Accounting Manual, chapter 3 (fictional)]
---

# Net Revenue

## Definition

> **Net Revenue** = Σ `journal_entry_line.amount_eur` of GL accounts with `account_group = 'REVENUE'`

| Account | Name | Sign |
|---|---|---|
| 3010 | Sales revenue DTC webshop | + |
| 3020 | Sales revenue B2B trade | + |
| 3090 | Returns and trade discounts | - |

Net of VAT, after returns and trade discounts, in **EUR**. The period is the fiscal year and period of the posting.

Reference (a user who sees every company code): **Jan-Sep 2026 = EUR 35.1 m**, Jan-Sep 2025 = EUR 33.0 m
(+6.4 %); full year 2025 = EUR 44.2 m.

## Business rules

1. Always EUR (`amount_eur`) when more than one company code is involved; never add `amount_local`.
2. "Revenue", "sales" and "turnover" all mean Net Revenue. Webshop GMV (consumer sample) is **not** revenue.
3. "Year to date" = January-September, compared with the same months of the prior year.

## How to calculate (SQL)

```sql
SELECT fiscal_year, MEASURE(net_revenue_eur) AS net_revenue_eur
FROM <catalog>.finance.net_revenue_metrics
GROUP BY ALL ORDER BY fiscal_year;

-- the same from the gold tables
SELECT l.fiscal_year, SUM(l.amount_eur) AS net_revenue_eur
FROM <catalog>.finance.journal_entry_line l
JOIN <catalog>.finance.gl_account a ON a.gl_account_code = l.gl_account_code
WHERE a.account_group = 'REVENUE'
GROUP BY ALL ORDER BY fiscal_year;
```

## Pitfalls

| Wrong answer | Why |
|---|---|
| Only accounts 3010 + 3020 | Gross revenue; forgets returns and trade discounts (3090) |
| `SUM(amount_local)` across company codes | Adds SEK, NOK, DKK, PLN and EUR |
| A full year 2026 | The data ends with September 2026 |

## Example questions

* What was net revenue by quarter in 2026?
* How does year-to-date revenue compare with last year?
