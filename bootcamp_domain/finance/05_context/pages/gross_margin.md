---
title: Gross Margin
domain: Finance
subdomain: General Ledger
synonyms: [gross profit, GM, gross margin %, GM%, margin, bruttomarginal]
description: "Gross Margin = Net Revenue - COGS (EUR, general ledger); Gross Margin % = Gross Margin ÷ Net Revenue, a ratio of sums."
owner: Group Financial Controller (role)
related_assets: [<catalog>.finance.net_revenue_metrics, <catalog>.finance.journal_entry_line, <catalog>.finance.gl_account]
sources: [Fjällmark Group Accounting Manual, chapter 3 (fictional)]
---

# Gross Margin

## Definition

> **Gross Margin** = Net Revenue - COGS
> **Gross Margin %** = 100 × Gross Margin ÷ Net Revenue

**COGS** = Σ `amount_eur` of accounts in `account_group = 'COGS'`: 4000 (cost of goods sold at standard) and
4100 (production variances). All amounts in EUR.

Reference: gross margin **45.1 %** in Jan-Sep 2026 (45.6 % in Jan-Sep 2025).

## Business rules

1. Gross margin % is a **ratio of sums** over the whole selection - never the average of monthly or per-company
   percentages.
2. Production variances (4100) are booked only by the producing entities SE01, FI01 and PL01, without a channel.
3. Brand margins: group by `brand`; lines without a brand are OPEX and not part of the gross margin.

## How to calculate (SQL)

```sql
SELECT brand, MEASURE(net_revenue_eur) AS net_revenue_eur, MEASURE(cogs_eur) AS cogs_eur,
       MEASURE(gross_margin_pct) AS gross_margin_pct
FROM <catalog>.finance.net_revenue_metrics
WHERE fiscal_year = 2026 AND brand IS NOT NULL
GROUP BY ALL ORDER BY gross_margin_pct DESC;
```

## Known event

**March 2026, PL01:** COGS rose to about EUR 281 k (EUR 139 k in February, EUR 141 k in April) because of a
production variance of EUR 145 k: worn filler nozzles on the Poznań line PL-POZ-L2 (repaired 4 April 2026).
Mjuk Care's margin dips in that month.

## Pitfalls

| Wrong answer | Why |
|---|---|
| `AVG(gross_margin_pct)` over months | Unweighted; use the ratio of sums |
| COGS = account 4000 only | Forgets production variances (4100) |

## Example questions

* Which brand has the highest gross margin?
* What was the gross margin % by quarter in 2026?
