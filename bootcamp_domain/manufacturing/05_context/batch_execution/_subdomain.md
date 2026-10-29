---
title: Batch Execution
domain: Manufacturing
subdomain: Batch Execution
subdomain_tag: Manufacturing/Batch Execution
description: What was produced, how well and when. Production orders (one product on one line, with plan, actual finish, good and scrap quantities and cost) and the downtime events on the lines. Yield, scrap rate, on-time completion and downtime are calculated here.
tables: production_order, downtime_event
metric_views: production_metrics
---

# Batch Execution (Manufacturing)

| Table | Primary key | What it holds |
|---|---|---|
| `production_order` | `production_order_id` | product, line, planned / actual dates, status (`completed`, `in_progress`, `cancelled`), planned / good / scrap quantity, planned and actual cost (EUR), shift supervisor |
| `downtime_event` | `downtime_event_id` | stops during completed orders: date, reason, minutes |

Joins: `production_order.plant_code` → `plant`, `production_order.line_code` → `production_line`,
`downtime_event.production_order_id` → `production_order`. Metric view: `<catalog>.manufacturing.production_metrics`.

## Questions this sub-domain answers

* What is the yield by plant in 2026?
* Why did scrap spike in Poznań in March 2026?
* Which line has the lowest on-time completion rate?

Pages: [Yield](../pages/yield.md), [Downtime](../pages/downtime.md).
