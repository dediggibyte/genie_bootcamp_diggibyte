---
title: Return Rate
domain: Consumer
subdomain: Direct Sales
synonyms: [returns, return rate, return share, returnering]
description: "Returned webshop orders ÷ placed orders (delivered + returned), in percent."
owner: Head of E-commerce (role)
related_assets: [<catalog>.consumer.dtc_sales_metrics, <catalog>.consumer.dtc_order]
sources: [Fjällmark E-commerce KPI handbook (fictional)]
---

# Return Rate

## Definition

> **Return rate %** = 100 × orders with `order_status = 'returned'` ÷ placed orders (`delivered` + `returned`)

Cancelled orders are in neither the numerator nor the denominator. The rate is counted on **orders**, not on
order value.

Reference: **6.4 %** over all markets and months.

## Known event

**August 2026, DE01:** a carrier damaged parcels in Germany and the Netherlands; DE01's return rate jumped to
**16.9 %** that month.

## How to calculate (SQL)

```sql
SELECT country_code, MEASURE(return_rate_pct) AS return_rate_pct
FROM <catalog>.consumer.dtc_sales_metrics
GROUP BY ALL ORDER BY return_rate_pct DESC;
```

## Pitfalls

| Wrong answer | Why |
|---|---|
| Returned ÷ all orders incl. cancelled | Cancelled orders were never delivered |
| Returned value ÷ GMV | A value-based rate - say so if the user asks for it |

## Example questions

* Which market has the highest return rate, and why?
* How did the return rate of DE01 develop in 2026?
