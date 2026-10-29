---
title: GMV (Gross Merchandise Value)
domain: Consumer
subdomain: Direct Sales
synonyms: [GMV, gross merchandise value, webshop sales, order value, AOV, average order value]
description: "The value of placed webshop orders (delivered or returned, never cancelled), net of VAT and excl. shipping, in EUR. Average order value = GMV ÷ placed orders."
owner: Head of E-commerce (role)
related_assets: [<catalog>.consumer.dtc_sales_metrics, <catalog>.consumer.dtc_order, <catalog>.consumer.dtc_order_line]
sources: [Fjällmark E-commerce KPI handbook (fictional)]
---

# GMV - Gross Merchandise Value

## Definition

> **GMV** = Σ `dtc_order.order_amount_eur` of orders with `order_status` in (`delivered`, `returned`)
> **Average order value (AOV)** = GMV ÷ number of placed orders

Placed orders include later **returns** (GMV measures demand); **cancelled** orders never count. Amounts are net
of VAT and exclude shipping.

Reference (all markets): **Jan-Sep 2026 = EUR 53,373 from 2,292 orders (AOV EUR 23.29)**; Jan-Sep 2025 =
EUR 28,829 from 1,294 orders (AOV EUR 22.28).

## Business rules

1. Across markets use `order_amount_eur`; `order_amount_local` is in SEK, NOK, DKK or EUR.
2. GMV by brand or product comes from `dtc_order_line.line_amount_eur` joined to `product`, for placed orders.
3. GMV is not Net Revenue: finance books revenue after returns and discounts in the general ledger.

## How to calculate (SQL)

```sql
SELECT order_month, MEASURE(gmv_eur) AS gmv_eur, MEASURE(orders) AS orders,
       MEASURE(average_order_value_eur) AS aov_eur
FROM <catalog>.consumer.dtc_sales_metrics
WHERE order_year = 2026
GROUP BY ALL ORDER BY order_month;
```

## Pitfalls

| Wrong answer | Why |
|---|---|
| Including cancelled orders | They never became sales |
| Only delivered orders | That is net sales after returns, not GMV |
| `SUM(order_amount_local)` across markets | Adds different currencies |

## Example questions

* What is GMV by month in 2026?
* What is the average order value by loyalty tier?
