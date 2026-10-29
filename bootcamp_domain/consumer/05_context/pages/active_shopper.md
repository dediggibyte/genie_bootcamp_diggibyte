---
title: Active Shopper
domain: Consumer
subdomain: Customer Identity
synonyms: [active customer, active shoppers, buying shopper, aktiv kund]
description: "A registered shopper with at least one placed webshop order (delivered or returned) in the last 12 months, i.e. 2025-10-01 to 2026-09-30."
owner: CRM Manager (role)
related_assets: [<catalog>.consumer.dtc_sales_metrics, <catalog>.consumer.dtc_order, <catalog>.consumer.shopper]
sources: [Fjällmark CRM segmentation guideline (fictional)]
---

# Active Shopper

## Definition

> A shopper is **active** when they have at least one **placed** order (`delivered` or `returned`) in the
> **last 12 months**: 2025-10-01 to 2026-09-30 (the data ends 2026-09-30).

Reference: **1,081 active shoppers** of 1,200 registered (all markets).

## Business rules

1. Count **distinct** shoppers - a shopper with five orders counts once.
2. Registered shoppers without a placed order in the window are *inactive*, whatever their loyalty tier.
3. Report shoppers in aggregate only; never list names or e-mail addresses.

## How to calculate (SQL)

```sql
SELECT country_code, MEASURE(active_shoppers) AS active_shoppers
FROM <catalog>.consumer.dtc_sales_metrics
WHERE order_date BETWEEN DATE'2025-10-01' AND DATE'2026-09-30'
GROUP BY ALL ORDER BY country_code;
```

## Pitfalls

| Wrong answer | Why |
|---|---|
| `COUNT(*) FROM shopper` | Registered, not active |
| No date filter | "Ever bought", not active |
| Counting cancelled orders | A cancelled order is not a purchase |

## Example questions

* How many active shoppers do we have?
* How many active shoppers are Gold or Platinum members?
