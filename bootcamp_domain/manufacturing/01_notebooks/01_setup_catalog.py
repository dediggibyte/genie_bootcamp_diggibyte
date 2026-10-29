# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 01 · Set up your catalog and land the raw data
# MAGIC
# MAGIC **Genie domain sample Manufacturing (simplified).** Every participant already has their own Unity Catalog *catalog*,
# MAGIC named after their user (e.g. `labuser123_456` for `labuser123_456@vocareum.com`). This notebook does **not**
# MAGIC create a catalog; it prepares what the pipeline in step 2 needs inside yours:
# MAGIC
# MAGIC | step | what |
# MAGIC |---|---|
# MAGIC | 1 | work out **your catalog name** = your short user name (the bundle uses the same default) |
# MAGIC | 2 | find the sample folder and its CSV files (`01_data/`, 4 small tables) |
# MAGIC | 3 | check that **your catalog** exists (it is never created here) |
# MAGIC | 4 | create the **schemas** `manufacturing_landing`, `manufacturing_bronze`, `manufacturing_silver`, `manufacturing` (gold) and `manufacturing_governance` |
# MAGIC | 5 | create the **volume** `manufacturing_landing.raw_files` |
# MAGIC | 6 | **copy the CSV files** into the volume, one folder per table |
# MAGIC | 7 | **verify** the files against `01_data/manifest.json` |
# MAGIC
# MAGIC ▶ **How to run:** open this notebook in your **Git folder**, attach **Serverless** and click **Run all**.
# MAGIC
# MAGIC 🔁 **Safe to re-run:** existing schemas, volume and files are kept; nothing is copied twice. Every schema starts
# MAGIC with the sample name, so the Finance, Consumer and Manufacturing samples can share your catalog.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 · Parameters
# MAGIC
# MAGIC | widget | default | meaning |
# MAGIC |---|---|---|
# MAGIC | `catalog` | blank = `<your short user name>` | your catalog (already created for you) |
# MAGIC | `overwrite` | `false` | `true` copies the CSV files again (repairs only, before the first pipeline run) |

# COMMAND ----------

import json
import os
import re
import shutil
import unicodedata

dbutils.widgets.text("catalog", "", "Catalog (blank = automatic)")
dbutils.widgets.dropdown("overwrite", "false", ["false", "true"], "Overwrite CSV files")

SAMPLE = "manufacturing"   # also the name of the gold schema


def bundle_short_name(user_name: str) -> str:
    """Same rule as the bundle's ${workspace.current_user.short_name}: the part before '@',
    lower-cased, every character that is not a letter or digit replaced by '_'."""
    local = user_name.split("@")[0].lower()
    return "".join(c if unicodedata.category(c).startswith("L") or unicodedata.category(c) == "Nd" else "_"
                   for c in local)


user_name = spark.sql("SELECT current_user()").first()[0]
catalog = dbutils.widgets.get("catalog").strip() or bundle_short_name(user_name)
if not re.fullmatch(r"[A-Za-z0-9_]+", catalog):
    # The pipeline SQL uses the catalog name without back-quotes: ASCII letters, digits and '_' only.
    raise ValueError(f"Catalog name {catalog!r} may only contain ASCII letters, digits and '_'. Type your catalog "
                     f"into the 'catalog' widget and deploy the bundle with the same name "
                     f"(--var catalog=<name>, or variables.catalog.default in databricks.yml).")
overwrite = dbutils.widgets.get("overwrite") == "true"

print(f"You are : {user_name}")
print(f"Catalog : {catalog}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 · Find the sample folder
# MAGIC
# MAGIC The notebook walks up from its own path to the folder that holds `databricks.yml` (= `bootcamp_domain/manufacturing/`).
# MAGIC The CSV files and `manifest.json` are in `01_data/` of that folder - the sample is self-contained.

# COMMAND ----------


def bundle_root() -> str:
    """The folder that holds databricks.yml (this notebook lives somewhere below it)."""
    try:
        nb_path = dbutils.notebook.entry_point.getDbutils().notebook().getContext().notebookPath().get()
        d = os.path.dirname(nb_path if nb_path.startswith("/Workspace") else "/Workspace" + nb_path)
    except Exception:  # fallback: notebooks run with the notebook folder as working directory
        d = os.getcwd()
    while d not in ("", "/"):
        if os.path.isfile(f"{d}/databricks.yml"):
            return d
        d = os.path.dirname(d)
    raise FileNotFoundError("databricks.yml not found above this notebook - run it from the Git folder.")


BUNDLE_ROOT = bundle_root()
with open(f"{BUNDLE_ROOT}/01_data/manifest.json", encoding="utf-8") as fh:
    manifest = json.load(fh)["tables"]
print(f"Sample folder : {BUNDLE_ROOT}")
print(f"Tables        : {', '.join(manifest)} ({sum(m['rows'] for m in manifest.values()):,} rows)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 · Check your catalog
# MAGIC
# MAGIC Your catalog was created for you before the workshop - this notebook never creates one. If it is not found,
# MAGIC look up its name in **Catalog** (under *My organization*), type it into the `catalog` widget and run again.

# COMMAND ----------


def sql_str(text: str) -> str:
    return "'" + text.replace("\\", "\\\\").replace("'", "\\'") + "'"


if spark.sql(f"SHOW CATALOGS LIKE {sql_str(catalog)}").count() == 0:
    raise RuntimeError(f"Catalog `{catalog}` not found. Type the name of your catalog (Catalog -> My organization) "
                       f"into the 'catalog' widget, run again, and deploy the bundle with --var catalog=<name>.")
print(f"✅ Catalog `{catalog}` found.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 · Create the schemas
# MAGIC
# MAGIC | schema | holds |
# MAGIC |---|---|
# MAGIC | `manufacturing_landing` | the volume `raw_files` with the CSV files |
# MAGIC | `manufacturing_bronze` | raw rows, every column a string |
# MAGIC | `manufacturing_silver` | typed and de-duplicated rows |
# MAGIC | `manufacturing` | **gold**: the tables Genie and the business query, plus the metric views |
# MAGIC | `manufacturing_governance` | the mapping table and the row-filter function (notebook 03) |

# COMMAND ----------

SCHEMAS = {
    f"{SAMPLE}_landing": "Landing zone: volume raw_files holds the CSV files (one folder per table).",
    f"{SAMPLE}_bronze": "Bronze: raw rows exactly as delivered, every column STRING. Written by genie_manufacturing_pipeline.",
    f"{SAMPLE}_silver": "Silver: typed, cleaned and de-duplicated rows. Written by genie_manufacturing_pipeline.",
    SAMPLE: "Manufacturing (gold): plants, production lines, production orders and downtime of Fjällmark Consumer Goods AB. Simplified domain sample.",
    f"{SAMPLE}_governance": "Governance: the access-mapping table and the row-filter function (notebook 03).",
}
for schema, comment in SCHEMAS.items():
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{catalog}`.`{schema}` COMMENT {sql_str(comment)}")
display(spark.sql(f"SHOW SCHEMAS IN `{catalog}` LIKE '{SAMPLE}*'"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5 · Create the landing volume

# COMMAND ----------

spark.sql(f"CREATE VOLUME IF NOT EXISTS `{catalog}`.`{SAMPLE}_landing`.`raw_files` "
          f"COMMENT 'CSV files of the Fjällmark manufacturing sample: <table>/<table>.csv'")
VOLUME_ROOT = f"/Volumes/{catalog}/{SAMPLE}_landing/raw_files"
print(f"✅ Volume ready: {VOLUME_ROOT}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6 · Copy the CSV files into the volume
# MAGIC
# MAGIC Each table gets its **own folder** - the pipeline's Auto Loader reads one folder per table, and ingests every
# MAGIC file **once**. A file that is already there is skipped. `overwrite = true` only helps *before* the first
# MAGIC pipeline run: a file replaced later is not read again.

# COMMAND ----------

results = []
for table, meta in manifest.items():
    src = f"{BUNDLE_ROOT}/{meta['file']}"
    dst = f"{VOLUME_ROOT}/{table}/{table}.csv"
    if os.path.exists(dst) and not overwrite:
        status = "already there" if os.path.getsize(dst) == os.path.getsize(src) else "DIFFERENT - kept"
    else:
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        status = "copied"
    results.append((table, status))
    print(f"{table:24} {status}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7 · Verify the landed files
# MAGIC
# MAGIC Every table folder must hold exactly one CSV with the number of data rows that `01_data/manifest.json` lists.

# COMMAND ----------

summary, problems = [], []
for table, meta in manifest.items():
    folder = f"{VOLUME_ROOT}/{table}"
    files = sorted(f for f in os.listdir(folder) if not f.startswith("."))
    with open(f"{folder}/{table}.csv", encoding="utf-8") as fh:
        rows = sum(1 for _ in fh) - 1
    ok = files == [f"{table}.csv"] and rows == meta["rows"]
    summary.append((table, meta["rows"], rows, "OK" if ok else "PROBLEM"))
    if not ok:
        problems.append(f"{table}: files={files}, rows={rows} (expected {meta['rows']})")
display(spark.createDataFrame(summary, "table string, expected_rows long, csv_rows long, status string"))
if problems:
    raise RuntimeError(f"{len(problems)} table folder(s) are not as expected: {problems}")
print(f"✅ {len(summary)} CSV files verified in {VOLUME_ROOT}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8 · Next: deploy and run the bundle
# MAGIC
# MAGIC 1. In the Git folder open `bootcamp_domain/manufacturing/databricks.yml`.
# MAGIC 2. Click the **Deployments** icon (🚀), choose target **`dev`** and click **Deploy**.
# MAGIC 3. Under *Bundle resources* run the job **`genie_manufacturing_job`**: `pipeline` → `metric_views` → `validate`.
# MAGIC
# MAGIC CLI alternative, from `bootcamp_domain/manufacturing/`: `databricks bundle deploy -t dev` and
# MAGIC `databricks bundle run genie_manufacturing_job -t dev` (add `--var catalog=<name>` if you typed another catalog above).

# COMMAND ----------

print(f"✅ Setup complete for catalog `{catalog}`.\n"
      f"NEXT: bootcamp_domain/{SAMPLE}/databricks.yml -> Deployments -> dev -> Deploy -> run genie_{SAMPLE}_job")
dbutils.notebook.exit(json.dumps({"catalog": catalog, "files": dict(results)}))
