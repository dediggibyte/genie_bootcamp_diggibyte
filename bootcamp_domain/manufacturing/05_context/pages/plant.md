---
title: Plant
domain: Manufacturing
subdomain: Asset Configuration
synonyms: [plant, site, factory, production line, line, fabrik]
description: "Fjällmark's four plants SE-LUN (Lund, food), SE-NKP (Norrköping, beverages), FI-TMP (Tampere, oat drinks, since April 2025) and PL-POZ (Poznań, personal care), each with three lines named <plant>-L<n>."
owner: Chief Operating Officer (role)
related_assets: [<catalog>.manufacturing.plant, <catalog>.manufacturing.production_line]
sources: [Fjällmark plant register (fictional)]
---

# Plant

## Definition

A **plant** is a manufacturing site, identified by `plant_code` (`<country>-<city>`). Each plant has three
**production lines**, coded `<plant_code>-L<n>`.

| Plant | Name | Company code | Brand | Lines |
|---|---|---|---|---|
| SE-LUN | Lund Food Plant | SE01 | Björkö Pantry | crispbread, granola, porridge and jam |
| SE-NKP | Norrköping Beverage Plant | SE01 | Kallkälla | sparkling water (bottles, cans), juice |
| FI-TMP | Tampere Oat Drink Plant | FI01 | Kallkälla | oat base, filling, packing - **since April 2025** |
| PL-POZ | Poznań Personal Care Plant | PL01 | Mjuk Care | deodorant, **L2 = liquid filling (shampoo, body wash)**, hand cream |

## Business rules

1. Filter and group by `plant_code`; `plant_name` is for display.
2. FI-TMP has no production before April 2025 - compare it year on year only from 2026.
3. Plant and line master data is not row-filtered; production orders and downtime are (notebook 03).

## How to look it up (SQL)

```sql
SELECT p.plant_code, p.plant_name, l.line_code, l.line_name, l.scrap_target_pct
FROM <catalog>.manufacturing.plant p
JOIN <catalog>.manufacturing.production_line l ON l.plant_code = p.plant_code
ORDER BY l.line_code;
```

## Example questions

* Which lines does the Poznań plant have?
* Which plant makes Kallkälla oat drinks?
