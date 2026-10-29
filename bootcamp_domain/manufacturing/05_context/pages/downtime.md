---
title: Downtime
domain: Manufacturing
subdomain: Batch Execution
synonyms: [downtime, stop time, line stop, stoppage, stillestånd]
description: "Minutes a production line stood still during a completed production order, from downtime_event.duration_min, by reason: changeover, mechanical_failure, material_shortage, cleaning, quality_hold."
owner: Head of Maintenance (role)
related_assets: [<catalog>.manufacturing.downtime_event, <catalog>.manufacturing.production_metrics]
sources: [Fjällmark Manufacturing KPI standard (fictional)]
---

# Downtime

## Definition

> **Downtime** = Σ `downtime_event.duration_min` (report in hours = minutes ÷ 60)

Each event belongs to one completed production order and has one **reason**:

| Reason | Planned? |
|---|---|
| `changeover` | planned |
| `cleaning` | planned |
| `mechanical_failure` | unplanned |
| `material_shortage` | unplanned |
| `quality_hold` | unplanned |

Reference: **PL-POZ-L2 lost about 58.5 hours in March 2026**, almost all `mechanical_failure` (worn filler nozzles).

## How to calculate (SQL)

```sql
SELECT line_code, reason, ROUND(SUM(duration_min) / 60, 1) AS downtime_hours
FROM <catalog>.manufacturing.downtime_event
WHERE event_date BETWEEN DATE'2026-03-01' AND DATE'2026-03-31'
GROUP BY ALL ORDER BY downtime_hours DESC;
```

The metric view `production_metrics` carries `downtime_minutes` per production order, so downtime can be
compared with yield on the same grain.

## Pitfalls

| Wrong answer | Why |
|---|---|
| Counting events instead of minutes | One long stop outweighs many short ones |
| Mixing planned and unplanned stops | Say which you report |

## Example questions

* What are the main downtime reasons per plant?
* How much downtime did PL-POZ-L2 have in March 2026?
