# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 02b · Validate the lakehouse (job task `validate`)
# MAGIC
# MAGIC | check | passes when |
# MAGIC |---|---|
# MAGIC | gold tables | all 4 exist in schema `consumer` with a primary key; 3 foreign keys are registered |
# MAGIC | row counts | silver has exactly the rows of `01_data/manifest.json`, with unique, non-NULL keys |
# MAGIC | gold = silver | for tables without a row filter (once notebook 03 ran, you only see your rows in gold) |
# MAGIC | metric views | every view in `02_metric_views/` answers a query |
# MAGIC
# MAGIC The task fails with a list of problems, so the job run turns red when something is missing.

# COMMAND ----------

import glob
import json
import os
import re
import unicodedata

dbutils.widgets.text("catalog", "", "Catalog (blank = automatic)")
SAMPLE = "consumer"
EXPECTED_FKS = 3


def bundle_short_name(user_name: str) -> str:
    local = user_name.split("@")[0].lower()
    return "".join(c if unicodedata.category(c).startswith("L") or unicodedata.category(c) == "Nd" else "_"
                   for c in local)


def bundle_root() -> str:
    try:
        nb_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
        d = os.path.dirname(nb_path if nb_path.startswith("/Workspace") else "/Workspace" + nb_path)
    except Exception:
        d = os.getcwd()
    while d not in ("", "/"):
        if os.path.isfile(f"{d}/databricks.yml"):
            return d
        d = os.path.dirname(d)
    raise FileNotFoundError("databricks.yml not found above this notebook.")


user_name = spark.sql("SELECT current_user()").first()[0]
catalog = dbutils.widgets.get("catalog").strip() or bundle_short_name(user_name)
BUNDLE_ROOT = bundle_root()
with open(f"{BUNDLE_ROOT}/01_data/manifest.json", encoding="utf-8") as fh:
    manifest = json.load(fh)["tables"]
C = f"`{catalog}`"
problems = []
print(f"Catalog: {catalog}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 · Gold tables, primary and foreign keys

# COMMAND ----------

existing = {r.table_name: r.table_type for r in spark.sql(f"""
    SELECT table_name, table_type FROM {C}.information_schema.tables
    WHERE table_schema = '{SAMPLE}' AND table_name NOT LIKE '\\_\\_%' AND table_name NOT LIKE 'event\\_log%'""").collect()}
pk = {r.table_name: r.column_name for r in spark.sql(f"""
    SELECT tc.table_name, kcu.column_name
    FROM {C}.information_schema.table_constraints tc
    JOIN {C}.information_schema.key_column_usage kcu
      ON kcu.constraint_schema = tc.constraint_schema AND kcu.constraint_name = tc.constraint_name
    WHERE tc.table_schema = '{SAMPLE}' AND tc.constraint_type = 'PRIMARY KEY'""").collect()}
n_fks = spark.sql(f"""SELECT count(*) FROM {C}.information_schema.table_constraints
                      WHERE table_schema = '{SAMPLE}' AND constraint_type = 'FOREIGN KEY'""").first()[0]
missing = [t for t in manifest if t not in existing]
no_pk = [t for t in manifest if t in existing and t not in pk]
if missing:
    problems.append(f"gold tables missing: {missing}")
if no_pk:
    problems.append(f"gold tables without a primary key: {no_pk}")
if n_fks < EXPECTED_FKS:
    problems.append(f"only {n_fks} of {EXPECTED_FKS} foreign keys - run the job again (the first pipeline run "
                    f"may register the keys in its automatic retry)")
print(f"gold tables {len(manifest) - len(missing)}/{len(manifest)}, primary keys {len(pk)}, foreign keys {n_fks}/{EXPECTED_FKS}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 · Row counts and key uniqueness
# MAGIC
# MAGIC Counted on **silver** (not governed, the same for every user) and compared with the manifest. Gold must equal
# MAGIC silver unless the table carries a row filter (step 3), then gold shows only *your* rows.

# COMMAND ----------

row_filtered = {r.table_name for r in spark.sql(
    f"SELECT table_name FROM {C}.information_schema.row_filters WHERE table_schema = '{SAMPLE}'").collect()}
stats = []
for t, meta in manifest.items():
    if t not in pk:
        continue
    k = pk[t]
    s = spark.sql(f"SELECT count(*) AS n, count(DISTINCT `{k}`) AS d FROM {C}.{SAMPLE}_silver.`{t}`").first()
    g = spark.sql(f"SELECT count(*) FROM {C}.`{SAMPLE}`.`{t}`").first()[0]
    stats.append((t, meta["rows"], s.n, s.d, g, t in row_filtered))
    if s.n != meta["rows"]:
        problems.append(f"{t}: silver has {s.n} rows, the manifest {meta['rows']}")
    if s.d != s.n:
        problems.append(f"{t}: {s.n - s.d} duplicate keys in silver")
    if t not in row_filtered and g != s.n:
        problems.append(f"{t}: gold {g} rows, silver {s.n} - run the job again")
display(spark.createDataFrame(stats, "table string, manifest_rows long, silver_rows long, distinct_keys long, "
                                     "gold_rows_you_see long, row_filter boolean"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 · Every metric view answers a query

# COMMAND ----------

mv_results = []
for path in sorted(glob.glob(f"{BUNDLE_ROOT}/02_metric_views/*.sql")):
    with open(path, encoding="utf-8") as fh:
        name = re.search(r"CREATE OR REPLACE VIEW\s+\$\{catalog\}\.([\w.`]+)", fh.read()).group(1).replace("`", "")
    fqn = f"{C}.{name}"
    try:
        desc = json.loads(spark.sql(f"DESCRIBE TABLE EXTENDED {fqn} AS JSON").first()[0])
        measure = next(c["name"] for c in desc["columns"] if c.get("is_measure"))
        value = spark.sql(f"SELECT MEASURE(`{measure}`) FROM {fqn}").first()[0]
        mv_results.append((name, measure, str(value), "OK"))
    except Exception as e:
        mv_results.append((name, None, None, "ERROR: " + str(e)[:300]))
        problems.append(f"metric view {name} not queryable")
display(spark.createDataFrame(mv_results, "metric_view string, measure string, value string, status string"))

# COMMAND ----------

if problems:
    raise RuntimeError("Validation FAILED: " + " || ".join(problems))
print(f"✅ Lakehouse validated: {len(stats)} gold tables, {n_fks} foreign keys, {len(mv_results)} metric views in `{catalog}`.")
dbutils.notebook.exit(json.dumps({"catalog": catalog, "tables": len(stats), "foreign_keys": n_fks,
                                  "metric_views": len(mv_results), "row_filtered": sorted(row_filtered)}))
