---
title: General Ledger
domain: Finance
subdomain: General Ledger
subdomain_tag: Finance/General Ledger
description: Every P&L posting of the group. Company codes, the chart of accounts and monthly general-ledger lines per company code, account, brand and channel, with amounts in local currency and EUR. Net Revenue, COGS and gross margin are calculated here.
tables: company_code, gl_account, journal_entry_line
metric_views: net_revenue_metrics
---

# General Ledger (Finance)

Every P&L posting of the group, one line per company code, month, GL account, brand and channel.

| Table | Primary key | What it holds |
|---|---|---|
| `company_code` | `company_code` | the six legal entities: SE01 (SEK, parent), NO01 (NOK), DK01 (DKK), FI01 (EUR), DE01 (EUR), PL01 (PLN) |
| `gl_account` | `gl_account_code` | eight accounts; `account_group` REVENUE, COGS or OPEX |
| `journal_entry_line` | `journal_entry_line_id` | monthly GL lines; `amount_eur` = P&L amount in EUR (revenue +, returns -, costs +) |

Joins: `journal_entry_line.company_code` → `company_code`, `journal_entry_line.gl_account_code` → `gl_account`.
Metric view: `<catalog>.finance.net_revenue_metrics`.

## Questions this sub-domain answers

* What was net revenue by company code in Q2 2026?
* Which brand has the highest gross margin?
* Why did COGS spike for PL01 in March 2026?

Pages: [Net Revenue](../pages/net_revenue.md), [Gross Margin](../pages/gross_margin.md).
