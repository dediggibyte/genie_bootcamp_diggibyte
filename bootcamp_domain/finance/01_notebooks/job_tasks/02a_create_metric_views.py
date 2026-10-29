# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 02a · Create the metric views (job task `metric_views`)
# MAGIC
# MAGIC A **metric view** holds a business definition once - *what is net revenue* - so that SQL, dashboards and
# MAGIC Genie all compute it the same way. This task runs every file in `02_metric_views/`
# MAGIC (`CREATE OR REPLACE VIEW ... WITH METRICS LANGUAGE YAML`), with `${catalog}` replaced by your catalog.
# MAGIC
# MAGIC 🔁 A view whose YAML is unchanged is left alone, so its tags (notebook 05) and Genie's view of it stay as they are.

# COMMAND ----------

import glob
import json
import os
import re
import unicodedata

dbutils.widgets.text("catalog", "", "Catalog (blank = automatic)")
SAMPLE = "finance"


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
print(f"Catalog: {catalog}")

try:
    import yaml
except ImportError:      # without PyYAML every view is simply replaced (still correct)
    yaml = None

# COMMAND ----------

results = []
for path in sorted(glob.glob(f"{BUNDLE_ROOT}/02_metric_views/*.sql")):
    with open(path, encoding="utf-8") as fh:
        sql = fh.read().replace("${catalog}", catalog)
    name = re.search(r"CREATE OR REPLACE VIEW\s+([\w.`]+)", sql).group(1).replace("`", "")
    want = yaml.safe_load(re.search(r"\$\$(.*)\$\$", sql, re.S).group(1)) if yaml else None
    try:
        desc = json.loads(spark.sql(f"DESCRIBE TABLE EXTENDED {name} AS JSON").first()[0])
        have = yaml.safe_load(desc.get("view_text") or "") if yaml else None
        exists = True
    except Exception:
        have, exists = None, False
    if exists and want is not None and want == have:
        results.append((name, os.path.basename(path), "unchanged"))
        continue
    spark.sql(sql)
    results.append((name, os.path.basename(path), "replaced" if exists else "created"))
display(spark.createDataFrame(results, "metric_view string, file string, status string"))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Try one
# MAGIC Metric views are queried with `MEASURE(<measure>)` and `GROUP BY` any of their dimensions:

# COMMAND ----------

display(spark.sql(f"""SELECT fiscal_year, MEASURE(net_revenue_eur) AS net_revenue_eur, MEASURE(gross_margin_pct) AS gross_margin_pct
    FROM `{catalog}`.finance.net_revenue_metrics GROUP BY ALL ORDER BY fiscal_year"""))

# COMMAND ----------

dbutils.notebook.exit(json.dumps({"catalog": catalog, "metric_views": {r[0]: r[2] for r in results}}))
