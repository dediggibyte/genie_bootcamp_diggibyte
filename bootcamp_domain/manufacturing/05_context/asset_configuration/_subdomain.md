---
title: Asset Configuration
domain: Manufacturing
subdomain: Asset Configuration
subdomain_tag: Manufacturing/Asset Configuration
description: Plants and production lines. The four plants (Lund, Norrköping, Tampere, Poznań) with country, company code and brand, and their twelve production lines with product category and scrap target.
tables: plant, production_line
metric_views:
---

# Asset Configuration (Manufacturing)

| Table | Primary key | What it holds |
|---|---|---|
| `plant` | `plant_code` | SE-LUN, SE-NKP, FI-TMP, PL-POZ with name, country, company code, main brand, commissioning date |
| `production_line` | `line_code` | 12 lines (`<plant>-L1..L3`) with name, product category and scrap target % |

Join: `production_line.plant_code` → `plant`. Master data is **not** row-filtered: everybody may name plants and lines.

## Questions this sub-domain answers

* Which lines does the Poznań plant have?
* What is the scrap target of PL-POZ-L2?

Page: [Plant](../pages/plant.md).
