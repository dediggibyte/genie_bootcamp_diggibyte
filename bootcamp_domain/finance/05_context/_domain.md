---
title: Finance
domain: Finance
domain_tag: Finance
subtitle: Legal entities, general ledger and receivables
description: Owns financial accounting for the Fjällmark group - company codes, chart of accounts, general-ledger postings and B2B receivables. The authoritative source for revenue, margin and cash KPIs in group currency EUR.
business_owner: Group Financial Controller (role)
schema: <catalog>.finance
---

# Finance

Finance is the **single source of truth for money** at Fjällmark Consumer Goods AB (a fictional company). When a
question is about revenue, margin, cost or receivables, the answer comes from this domain, in **group currency
EUR**, by **company code** and **fiscal period**.

| | |
|---|---|
| Business owner | Group Financial Controller (role) |
| Gold schema | `<catalog>.finance` - governed tag `Finance` |
| Row-level security | analysts see only the company codes they are mapped to (notebook 03) |
| Personal data | `ar_invoice.customer_contact_email` is masked |

## Sub-domains

| Sub-domain (tag) | Tables | Metric view |
|---|---|---|
| [General Ledger](general_ledger/_subdomain.md) (`Finance/General Ledger`) | `company_code`, `gl_account`, `journal_entry_line` | `net_revenue_metrics` |
| [Receivables Payables](receivables_payables/_subdomain.md) (`Finance/Receivables Payables`) | `ar_invoice` | `receivables_metrics` |

## Pages

| Page | One-liner |
|---|---|
| [Net Revenue](pages/net_revenue.md) | **The** revenue: GL revenue accounts incl. returns and trade discounts, EUR |
| [Gross Margin](pages/gross_margin.md) | Net Revenue - COGS, and as % of Net Revenue |
| [DSO](pages/dso.md) | Open receivables ÷ (credit sales of the last quarter ÷ 92 days) |

## Rules of thumb

1. Revenue questions → **Net Revenue** in EUR from the general ledger.
2. Across company codes → `amount_eur` only, never `amount_local`.
3. Periods → `fiscal_year` / `fiscal_period` (calendar year, month 1-12). Data: January 2025 - September 2026.
4. Receivables are a snapshot **as of 2026-09-30**.
