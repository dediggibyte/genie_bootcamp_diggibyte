# Genie, Governed: simplified domain samples

Three small, standalone samples of the Genie bootcamp lab, **one per business domain**. Each one is a complete
lab for a single team: its own catalog, a bronze/silver/gold pipeline, governance, one Genie Agent and the
business context (domain, sub-domains, Pages) of its domain.

They are a simplified rework of the `bootcamp_domain/` samples in
[`dediggibyte/genie_bootcamp`](https://github.com/dediggibyte/genie_bootcamp/tree/main/bootcamp_domain): the same
fictional company (Fjällmark Consumer Goods AB), the same steps and notebooks, but a much smaller data model.

| sample | for whom | gold tables (rows) | metric views | row filter on | Pages |
|---|---|---|---|---|---|
| [`finance/`](finance/README.md) | finance and controlling | 4 (3,000) | `net_revenue_metrics`, `receivables_metrics` | `company_code` | Net Revenue, Gross Margin, DSO |
| [`consumer/`](consumer/README.md) | e-commerce, CRM | 4 (14,800) | `dtc_sales_metrics` | `company_code` (market) | GMV, Return Rate, Active Shopper |
| [`manufacturing/`](manufacturing/README.md) | plants and operations | 4 (2,300) | `production_metrics` | `plant_code` | Plant, Yield, Downtime |

## What was simplified

| | original samples | these samples |
|---|---|---|
| **dataset** | 11-16 industry-model tables per sample, 25-50 columns each, up to 17,000 rows per table, injected data-quality issues, CSVs shared from `bootcamp/data/` | **4 tables** per sample, 3-16 columns, every amount also in **EUR** (no FX joins), clean data, CSVs inside the sample (`01_data/`) |
| **pipeline** | generated SQL, enum mapping, multi-format dates, up to 42 foreign keys | short hand-written SQL, **3-4 foreign keys** |
| **metric views** | 6-8 industry + 1-2 curated views, model tags (`dbx_*`) | **1-2 curated views**, no model tags |
| **governance** | several row filters (some via lookups), up to 13 masks, buddy test, ABAC, nested-policy demo | **one row filter** on one column (`company_code`, or `plant_code` for manufacturing), driven by your user id (`current_user()`) and one mapping table; no masks |
| **domain** | 3 sub-domains from the industry model | **2 sub-domains**, read from `05_context/` |
| **pages** | 9 per domain in `bootcamp/context/` | **3 per domain** in the sample's own `05_context/pages/` |
| **Genie Agent** | 8-12 data sources, 7-9 benchmarks | 5 data sources, **5 benchmarks** |

Sub-domain names match the original domains (for example `Finance/General Ledger`), so the samples work next to
the full bootcamp in the same account. The catalogs are named `genie_<sample>_<short name>` so they never collide
with the original `cpg_<sample>_<short name>` catalogs.

## The steps (the same in every sample)

| step | file | what it does |
|---|---|---|
| 0 | `01_notebooks/00_instructor_setup.py`, `00_INSTRUCTOR.md` | admins, once per workshop: governed tags, domain and sub-domains, ASSIGN for participants |
| 1 | `01_notebooks/01_setup_catalog.py` | catalog, schemas, volume; copies the CSV files from `01_data/` |
| 2 | `databricks.yml`, `resources/`, `01_notebooks/job_tasks/` | bundle: pipeline `genie_<sample>_pipeline` and job `genie_<sample>_job` (pipeline → metric views → validate) |
| 3 | `01_notebooks/03_governance.py` | your user id → mapping table → one row filter on `company_code` / `plant_code` |
| 4 | `01_notebooks/04_genie_agent.py` | creates or updates the Genie Agent, a test question, the benchmarks |
| 5 | `01_notebooks/05_business_context.py` | domain and sub-domain tags, Bulk import prompt for the Pages, GitHub MCP |
| - | `01_notebooks/99_cleanup.py` | removes what the sample created (dry run first) |

```text
<sample>/
  README.md, 00_INSTRUCTOR.md      participant guide, instructor guide
  01_data/                         4 CSV files + manifest.json
  01_notebooks/                    00, 01, 03, 04, 05, 99 and job_tasks/02a-02b
  databricks.yml, resources/       step 2: the bundle
  02_pipeline/, 02_metric_views/   step 2: what the bundle deploys
  04_genie/                        step 4: the Genie Agent template
  05_context/                      step 5: _domain.md, <sub-domain>/_subdomain.md, pages/, glossary.csv
```

## How to run a sample

1. Add this repository as a **Git folder** in your workspace (Workspace → Create → Git folder →
   `https://github.com/dediggibyte/genie_bootcamp_diggibyte`).
2. Open `bootcamp_domain/<sample>/README.md` and follow steps 1 to 5.

Workspace prerequisites: serverless compute, `CAN USE` on a SQL warehouse, a catalog of your own (or the right
to create one). For step 5 an admin runs the sample's `00_instructor_setup.py` once; working alone you can skip it -
notebook 05 then skips the tags and still writes the Pages prompt.

> **Not yet run on a workspace.** The notebooks reuse the API calls and SQL patterns of the tested bootcamp, but
> these simplified samples have not been deployed end to end yet.

## For maintainers

The data, the manifests and the Genie Agent templates are generated by one script (standard library only,
deterministic):

```bash
python3 -I bootcamp_domain/tools/build_samples.py           # write the generated files, print the reference KPIs
python3 -I bootcamp_domain/tools/build_samples.py --check   # exit 1 if a generated file is missing or stale
```

The notebooks, the pipeline SQL, the metric views and the `05_context/` pages are hand-written. When you change the
data generator, update the reference numbers in the Pages and in each sample's README (the script prints them).

**License.** The table names follow the Databricks *Lakehouse Industry Data Model, Consumer Goods v2 (MVM)*
(© Databricks, Inc.), used under the Databricks license: see [`LICENSE.md`](LICENSE.md) and [`NOTICE.md`](NOTICE.md).
The simplified tables, data, notebooks and agent content are modified for this repository.
