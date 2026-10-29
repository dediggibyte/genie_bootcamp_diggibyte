---
title: Consumer
domain: Consumer
domain_tag: Consumer
subtitle: Shoppers and the DTC webshop
description: Owns everything about end consumers of Fjällmark's brands - registered shoppers and their loyalty tier, and the direct-to-consumer webshop orders. The source for GMV, orders, returns and active shoppers.
business_owner: Head of E-commerce (role)
schema: <catalog>.consumer
---

# Consumer

The Consumer domain covers the **webshop `fjallmark.example`** of Fjällmark Consumer Goods AB (a fictional
company) in Sweden, Norway, Denmark, Finland, Germany and the Netherlands, and the shoppers who buy there.

| | |
|---|---|
| Business owner | Head of E-commerce (role) |
| Gold schema | `<catalog>.consumer` - governed tag `Consumer` |
| Row-level security | one row filter on `company_code`: each user sees only the markets mapped to their user id (notebook 03) |

## Sub-domains

| Sub-domain (tag) | Tables | Metric view |
|---|---|---|
| [Customer Identity](customer_identity/_subdomain.md) (`Consumer/Customer Identity`) | `shopper` | - |
| [Direct Sales](direct_sales/_subdomain.md) (`Consumer/Direct Sales`) | `product`, `dtc_order`, `dtc_order_line` | `dtc_sales_metrics` |

## Pages

| Page | One-liner |
|---|---|
| [GMV](pages/gmv.md) | Order value of placed (not cancelled) webshop orders, EUR, net of VAT |
| [Return Rate](pages/return_rate.md) | Returned orders ÷ placed orders |
| [Active Shopper](pages/active_shopper.md) | A shopper with at least one placed order in the last 12 months |

## Rules of thumb

1. Cancelled orders never count. Placed = delivered + returned.
2. Across markets → `order_amount_eur` / `line_amount_eur`, never `order_amount_local`.
3. GMV is an operational webshop figure, not revenue (Net Revenue is Finance's).
4. Data: January 2025 - September 2026; "last 12 months" = 2025-10-01 to 2026-09-30.
