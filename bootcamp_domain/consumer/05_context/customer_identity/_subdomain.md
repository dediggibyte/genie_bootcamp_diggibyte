---
title: Customer Identity
domain: Consumer
subdomain: Customer Identity
subdomain_tag: Consumer/Customer Identity
description: Who our shoppers are. One row per registered webshop shopper with market, Fjällmark Friends loyalty tier, sign-up date and marketing consent. Names and e-mail are personal data and masked.
tables: shopper
metric_views:
---

# Customer Identity (Consumer)

| Table | Primary key | What it holds |
|---|---|---|
| `shopper` | `shopper_id` | 1,200 shoppers: market (`country_code`, `company_code`), `loyalty_tier` (Bronze, Silver, Gold, Platinum or NULL), `signup_date`, `marketing_opt_in`; `given_name`, `family_name`, `email` are personal data |

Answer questions about shoppers **only in aggregate** - never list names or e-mail addresses.

## Questions this sub-domain answers

* How many active shoppers do we have per market?
* How are shoppers spread over the loyalty tiers?

Page: [Active Shopper](../pages/active_shopper.md).
