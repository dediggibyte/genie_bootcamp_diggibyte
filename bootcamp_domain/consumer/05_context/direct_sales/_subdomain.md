---
title: Direct Sales
domain: Consumer
subdomain: Direct Sales
subdomain_tag: Consumer/Direct Sales
description: The DTC webshop. The 12 products, every order with its status and value in market currency and EUR, and every order line. GMV, average order value and return rate are calculated here.
tables: product, dtc_order, dtc_order_line
metric_views: dtc_sales_metrics
---

# Direct Sales (Consumer)

| Table | Primary key | What it holds |
|---|---|---|
| `product` | `product_id` | 12 products of the three brands with list price in EUR |
| `dtc_order` | `order_id` | one row per order: shopper, market, date, status (`delivered`, `returned`, `cancelled`), value in market currency and EUR |
| `dtc_order_line` | `order_line_id` | product, quantity and amount (EUR) of each order line |

Joins: `dtc_order.shopper_id` → `shopper`, `dtc_order_line.order_id` → `dtc_order`,
`dtc_order_line.product_id` → `product`. Metric view: `<catalog>.consumer.dtc_sales_metrics`.

## Questions this sub-domain answers

* How did GMV develop month by month in 2026?
* What is the average order value by loyalty tier?
* Which market has the highest return rate?

Pages: [GMV](../pages/gmv.md), [Return Rate](../pages/return_rate.md).
