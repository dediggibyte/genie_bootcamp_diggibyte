# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 99 · Clean up after the Finance sample
# MAGIC
# MAGIC Removes what **you** created with this sample, and nothing else:
# MAGIC
# MAGIC | what | safeguard |
# MAGIC |---|---|
# MAGIC | your Genie Agent (to the trash, restorable for 30 days) | title `Fjällmark Finance Analyst (<catalog>)`, in **your** home folder |
# MAGIC | row filters and column masks | only in **this** catalog, and only if you own it |
# MAGIC | the catalog (`DROP CATALOG ... CASCADE`) | only if you own it |
# MAGIC | the bundle's job and pipeline | `bundle destroy` - see the last cell |
# MAGIC
# MAGIC Account-level objects (domains, governed tags, published Pages) are never touched.
# MAGIC
# MAGIC ▶ **Run all** once: it only lists what it would delete. Then type your catalog name into `confirm` and run again.

# COMMAND ----------

import json
import unicodedata

from databricks.sdk import WorkspaceClient

SAMPLE = "finance"
dbutils.widgets.text("catalog", "", "1 Catalog (blank = automatic)")
dbutils.widgets.text("confirm", "", "2 Type the catalog name to confirm")
dbutils.widgets.dropdown("drop_catalog", "true", ["true", "false"], "3 Drop the catalog")


def bundle_short_name(user_name: str) -> str:
    local = user_name.split("@")[0].lower()
    return "".join(c if unicodedata.category(c).startswith("L") or unicodedata.category(c) == "Nd" else "_"
                   for c in local)


w = WorkspaceClient()
me = spark.sql("SELECT current_user()").first()[0]
CAT = dbutils.widgets.get("catalog").strip() or f"genie_{SAMPLE}_{bundle_short_name(me)}"
Q = f"`{CAT}`"
CONFIRMED = dbutils.widgets.get("confirm").strip() == CAT
AGENT_TITLE = f"Fjällmark Finance Analyst ({CAT})"
print(f"Catalog: {CAT}\nMode   : {'DELETE' if CONFIRMED else 'DRY RUN (type the catalog name into confirm to delete)'}")

# COMMAND ----------

try:
    owner = w.catalogs.get(CAT).owner
    exists = True
except Exception:
    owner, exists = None, False
mine = exists and (owner or "").lower() == me.lower()
filters, masks = [], []
if exists:
    filters = [(r.table_schema, r.table_name) for r in spark.sql(
        f"SELECT table_schema, table_name FROM {Q}.information_schema.row_filters").collect()]
    masks = [(r.table_schema, r.table_name, r.column_name) for r in spark.sql(
        f"SELECT table_schema, table_name, column_name FROM {Q}.information_schema.column_masks").collect()]
agents, token = [], None
while True:
    resp = w.api_client.do("GET", "/api/2.0/genie/spaces", query={"page_size": 100, **({"page_token": token} if token else {})})
    for s in resp.get("spaces", []):
        if s.get("title") == AGENT_TITLE:
            d = w.api_client.do("GET", f"/api/2.0/genie/spaces/{s['space_id']}")
            if (d.get("parent_path") or "").removeprefix("/Workspace").startswith(f"/Users/{me}"):
                agents.append(s["space_id"])
    token = resp.get("next_page_token")
    if not token:
        break
print(f"catalog exists: {exists} (owner {owner}), row filters: {len(filters)}, column masks: {len(masks)}, agents: {agents}")
if exists and not mine:
    print("You do not own this catalog - its policies and data are left alone.")
if not CONFIRMED:
    dbutils.notebook.exit(json.dumps({"mode": "dry_run", "catalog": CAT, "agents": agents,
                                      "row_filters": len(filters), "column_masks": len(masks)}))

# COMMAND ----------

for space_id in agents:
    w.api_client.do("DELETE", f"/api/2.0/genie/spaces/{space_id}")
    print(f"trashed agent {space_id}")


def alter(schema: str, table: str) -> str:
    kind = spark.sql(f"SELECT table_type FROM {Q}.information_schema.tables WHERE table_schema = :s AND table_name = :t",
                     {"s": schema, "t": table}).first()[0]
    return f"ALTER {'MATERIALIZED VIEW' if kind == 'MATERIALIZED_VIEW' else 'TABLE'} {Q}.`{schema}`.`{table}`"


if mine:
    for schema, table in filters:
        spark.sql(f"{alter(schema, table)} DROP ROW FILTER")
    for schema, table, column in masks:
        spark.sql(f"{alter(schema, table)} ALTER COLUMN `{column}` DROP MASK")
    print(f"removed {len(filters)} row filter(s) and {len(masks)} column mask(s)")
    if dbutils.widgets.get("drop_catalog") == "true":
        spark.sql(f"DROP CATALOG IF EXISTS {Q} CASCADE")
        print(f"dropped catalog {CAT}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Remove the job and the pipeline
# MAGIC
# MAGIC Open `bootcamp_domain/finance/databricks.yml` → **Deployments** → target `dev` → **Destroy**, or from that
# MAGIC folder: `databricks bundle destroy -t dev --var catalog=<your catalog> --auto-approve`. Without the bundle,
# MAGIC delete `[dev <you>] genie_finance_job (<catalog>)` and `... genie_finance_pipeline ...` in **Jobs & Pipelines**.

# COMMAND ----------

left = spark.sql("SELECT count(*) FROM system.information_schema.catalogs WHERE catalog_name = :c", {"c": CAT}).first()[0]
dbutils.notebook.exit(json.dumps({"mode": "deleted", "catalog": CAT, "agents_trashed": agents, "catalog_left": left > 0}))
