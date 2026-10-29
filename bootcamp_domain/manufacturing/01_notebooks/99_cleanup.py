# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 99 · Clean up after the Manufacturing sample
# MAGIC
# MAGIC Removes what **you** created with this sample, and nothing else:
# MAGIC
# MAGIC | what | safeguard |
# MAGIC |---|---|
# MAGIC | your Genie Agent (to the trash, restorable for 30 days) | title `Fjällmark Manufacturing Analyst (<catalog>)`, in **your** home folder |
# MAGIC | this sample's schemas `manufacturing`, `manufacturing_landing`, `manufacturing_bronze`, `manufacturing_silver`, `manufacturing_governance` (`DROP SCHEMA ... CASCADE`: tables, metric views, volume, row filter) | only these five; **your catalog is kept**, and so are the other samples' schemas |
# MAGIC | the bundle's job and pipeline | `bundle destroy` - see the last cell |
# MAGIC
# MAGIC Account-level objects (domains, governed tags, published Pages) are never touched.
# MAGIC
# MAGIC ▶ **Run all** once: it only lists what it would delete. Then type your catalog name into `confirm` and run again.
# MAGIC
# MAGIC Remove the job and the pipeline (last cell) **first**: a running pipeline would recreate its tables.

# COMMAND ----------

import json
import unicodedata

from databricks.sdk import WorkspaceClient

SAMPLE = "manufacturing"
dbutils.widgets.text("catalog", "", "1 Catalog (blank = automatic)")
dbutils.widgets.text("confirm", "", "2 Type the catalog name to confirm")


def bundle_short_name(user_name: str) -> str:
    local = user_name.split("@")[0].lower()
    return "".join(c if unicodedata.category(c).startswith("L") or unicodedata.category(c) == "Nd" else "_"
                   for c in local)


w = WorkspaceClient()
me = spark.sql("SELECT current_user()").first()[0]
CAT = dbutils.widgets.get("catalog").strip() or bundle_short_name(me)
Q = f"`{CAT}`"
SCHEMAS = [SAMPLE] + [f"{SAMPLE}_{s}" for s in ("landing", "bronze", "silver", "governance")]
CONFIRMED = dbutils.widgets.get("confirm").strip() == CAT
AGENT_TITLE = f"Fjällmark Manufacturing Analyst ({CAT})"
print(f"Catalog: {CAT}\nMode   : {'DELETE' if CONFIRMED else 'DRY RUN (type the catalog name into confirm to delete)'}")

# COMMAND ----------

existing = {r.schema_name for r in spark.sql(
    "SELECT schema_name FROM system.information_schema.schemata WHERE catalog_name = :c", {"c": CAT}).collect()}
present = [s for s in SCHEMAS if s in existing]   # gold first: its row filter uses the governance function
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
print(f"schemas to drop: {present or 'none'}\nagents to trash: {agents or 'none'}")
if not CONFIRMED:
    dbutils.notebook.exit(json.dumps({"mode": "dry_run", "catalog": CAT, "schemas": present, "agents": agents}))

# COMMAND ----------

for space_id in agents:
    w.api_client.do("DELETE", f"/api/2.0/genie/spaces/{space_id}")
    print(f"trashed agent {space_id}")

for schema in present:
    spark.sql(f"DROP SCHEMA IF EXISTS {Q}.`{schema}` CASCADE")
    print(f"dropped schema {CAT}.{schema}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Remove the job and the pipeline
# MAGIC
# MAGIC Open `bootcamp_domain/manufacturing/databricks.yml` → **Deployments** → target `dev` → **Destroy**, or from that
# MAGIC folder: `databricks bundle destroy -t dev --var catalog=<your catalog> --auto-approve`. Without the bundle,
# MAGIC delete `[dev <you>] genie_manufacturing_job (<catalog>)` and `... genie_manufacturing_pipeline ...` in **Jobs & Pipelines**.

# COMMAND ----------

dbutils.notebook.exit(json.dumps({"mode": "deleted", "catalog": CAT, "schemas_dropped": present, "agents_trashed": agents}))
