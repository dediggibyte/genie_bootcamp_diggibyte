---
title: Manufacturing
domain: Manufacturing
domain_tag: Manufacturing
subtitle: Plants, lines, production orders and downtime
description: Owns production in Fjällmark's four plants - plant and line master data, production orders with quantities and cost, and line downtime. The source for yield, scrap, on-time completion and downtime KPIs.
business_owner: Chief Operating Officer (role)
schema: <catalog>.manufacturing
---

# Manufacturing

Production of Fjällmark Consumer Goods AB (a fictional company) in four plants with three lines each.

| | |
|---|---|
| Business owner | Chief Operating Officer (role) |
| Gold schema | `<catalog>.manufacturing` - governed tag `Manufacturing` |
| Row-level security | analysts see only the plants they are mapped to (notebook 03) |
| Confidential data | `production_order.actual_cost_eur` (cost) and `shift_supervisor` (personal data) are masked |

## Sub-domains

| Sub-domain (tag) | Tables | Metric view |
|---|---|---|
| [Asset Configuration](asset_configuration/_subdomain.md) (`Manufacturing/Asset Configuration`) | `plant`, `production_line` | - |
| [Batch Execution](batch_execution/_subdomain.md) (`Manufacturing/Batch Execution`) | `production_order`, `downtime_event` | `production_metrics` |

## Pages

| Page | One-liner |
|---|---|
| [Plant](pages/plant.md) | The four plants and how plants and lines are coded |
| [Yield](pages/yield.md) | Good ÷ (good + scrap) units of completed orders; scrap rate is the rest |
| [Downtime](pages/downtime.md) | Minutes a line stood still during production, by reason |

## Rules of thumb

1. Yield, scrap and on-time KPIs count **completed** orders only.
2. Ratios are ratios of sums, never averages of per-order percentages.
3. Data: January 2025 - September 2026; FI-TMP started in April 2025.
