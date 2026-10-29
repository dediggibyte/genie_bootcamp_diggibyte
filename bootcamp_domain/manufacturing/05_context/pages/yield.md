---
title: Yield
domain: Manufacturing
subdomain: Batch Execution
synonyms: [yield, first pass yield, scrap, scrap rate, waste, utbyte]
description: "Yield % = good units ÷ (good + scrap units) of completed production orders; scrap rate % = scrap ÷ (good + scrap). Ratios of sums."
owner: Head of Production (role)
related_assets: [<catalog>.manufacturing.production_metrics, <catalog>.manufacturing.production_order]
sources: [Fjällmark Manufacturing KPI standard (fictional)]
---

# Yield (and scrap rate)

## Definition

> **Yield %** = 100 × Σ `good_qty` ÷ Σ (`good_qty` + `scrap_qty`)
> **Scrap rate %** = 100 × Σ `scrap_qty` ÷ Σ (`good_qty` + `scrap_qty`) = 100 - yield %

Only **completed** production orders count. The period is the month of `actual_finish_date`.

Reference (2026): yield between **97.6 % and 98.3 %** in every plant. Line scrap targets are 1.5-3.0 %.

## Known event

**March 2026, PL-POZ-L2** (liquid filling): worn filler nozzles. Scrap rose to **9.6 %** (1.6 % in February,
3.4 % in April while the line ramped back up) until the repair on **4 April 2026**; the line also lost about
58 hours to mechanical failures in March (see [Downtime](downtime.md)).

## How to calculate (SQL)

```sql
SELECT plant_code, MEASURE(yield_pct) AS yield_pct, MEASURE(scrap_rate_pct) AS scrap_rate_pct
FROM <catalog>.manufacturing.production_metrics
WHERE finish_year = 2026
GROUP BY ALL ORDER BY plant_code;
```

## Pitfalls

| Wrong answer | Why |
|---|---|
| Including in_progress or cancelled orders | Their quantities are NULL or 0 |
| `good_qty / planned_qty` | That is plan attainment, not yield |
| Average of per-order yields | Unweighted; use the ratio of sums |

## Example questions

* What is the yield by plant in 2026?
* Why did scrap spike in Poznań in March 2026?
