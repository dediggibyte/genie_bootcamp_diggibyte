# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 03 · Governance — you only see the markets you are allowed to see
# MAGIC
# MAGIC Your gold tables are built, and right now **everybody who can read them sees everything**: the shoppers and orders of every market.
# MAGIC In this notebook you put **one Unity Catalog row filter** on the `company_code` column of the gold
# MAGIC tables, driven by **your user id** (`current_user()`). Because the filter lives *on the tables*, every consumer
# MAGIC inherits it: SQL, dashboards, the metric views and the **Genie Agent** of notebook 04.
# MAGIC
# MAGIC | step | what |
# MAGIC |---|---|
# MAGIC | 1 | parameters: your user id and the markets you may see |
# MAGIC | 2 | **before**: what you see without a filter |
# MAGIC | 3 | **mapping table**: your user id → `company_code` (*who may see what* is data, not code) |
# MAGIC | 4 | **row-filter function** `company_filter(company_code)` |
# MAGIC | 5 | **attach** it to the `company_code` column of the gold tables |
# MAGIC | 6 | **after**: the same query again, with checks |
# MAGIC | 7 | the **metric view inherits** the filter |
# MAGIC | 8 | *(optional)* rollback, summary |
# MAGIC
# MAGIC ▶ **How to run:** Serverless → **Run all**. Every statement is printed above its result.
# MAGIC
# MAGIC 🔁 **Re-running is a no-op**: the mapping row, the function and the filter are only written when missing or
# MAGIC different. To change what you see, change the `company_code` widget and run again - no pipeline run needed.
# MAGIC
# MAGIC > Members of the account group `cpg_bootcamp_admins` bypass the filter. Test as a non-admin.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 · Parameters
# MAGIC
# MAGIC | widget | default | meaning |
# MAGIC |---|---|---|
# MAGIC | `catalog` | blank = `genie_consumer_<short name>` | your catalog |
# MAGIC | `company_code` | `SE01` | the markets **you** may see: `SE01`, `SE01,NO01,DK01` or `ALL` |
# MAGIC | `rollback` | `false` | `true` = remove the filter, the function and the mapping table at the end (**leave it `false`**) |
# MAGIC
# MAGIC Markets (selling entities): `SE01` Sweden · `NO01` Norway · `DK01` Denmark · `FI01` Finland · `DE01` Germany and the Netherlands.

# COMMAND ----------

import json
import textwrap
import unicodedata

dbutils.widgets.text("catalog", "", "1 Catalog (blank = automatic)")
dbutils.widgets.text("company_code", "SE01", "2 Market(s): SE01 | SE01,NO01 | ALL")
dbutils.widgets.dropdown("rollback", "false", ["false", "true"], "3 Roll back at the end")

SAMPLE = "consumer"
ADMIN_GROUP = "cpg_bootcamp_admins"   # members bypass the filter (instructors)
ACCESS_TABLE = "user_company_access"       # governance.<ACCESS_TABLE>(user_email, <ACCESS_COLUMN>)
ACCESS_COLUMN = "company_code"     # the column the row filter is attached to
FILTER_FN = "company_filter"
# gold tables that carry ACCESS_COLUMN and get the row filter
ROW_FILTERED = ['consumer.shopper', 'consumer.dtc_order', 'consumer.dtc_order_line']


def bundle_short_name(user_name: str) -> str:
    local = user_name.split("@")[0].lower()
    return "".join(c if unicodedata.category(c).startswith("L") or unicodedata.category(c) == "Nd" else "_"
                   for c in local)


USER_ID = spark.sql("SELECT current_user()").first()[0]       # your user id = what the filter compares with
CATALOG = dbutils.widgets.get("catalog").strip() or f"genie_{SAMPLE}_{bundle_short_name(USER_ID)}"
C = f"`{CATALOG}`"
G = f"{C}.governance"
ACCESS = sorted({v.strip().upper() for v in dbutils.widgets.get("company_code").split(",") if v.strip()})
ROLLBACK = dbutils.widgets.get("rollback") == "true"
CHECKS, CHANGES = [], []
print(f"Your user id : {USER_ID}\nCatalog      : {CATALOG}\nYou may see  : {ACCESS_COLUMN} {', '.join(ACCESS)}")


def run(statement: str, args: dict | None = None, echo: bool = True):
    if echo:
        print(textwrap.dedent(statement).strip() + ";\n")
    return spark.sql(statement, args or {})


def check(name: str, ok: bool, detail: str = "") -> None:
    CHECKS.append((name, "PASS" if ok else "FAIL", detail))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" - {detail}" if detail else ""))


def alter(table: str) -> str:
    """Gold tables are pipeline MATERIALIZED VIEWs: ALTER TABLE fails on them, ALTER MATERIALIZED VIEW works."""
    schema, name = table.split(".")
    kind = run(f"SELECT table_type FROM {C}.information_schema.tables WHERE table_schema = :s AND table_name = :t",
               {"s": schema, "t": name}, echo=False).first()
    if kind is None:
        raise RuntimeError(f"{table} not found - run the bundle job genie_{SAMPLE}_job first (step 2).")
    return f"ALTER {'MATERIALIZED VIEW' if kind[0] == 'MATERIALIZED_VIEW' else 'TABLE'} {C}.{table}"


IS_ADMIN = run(f"SELECT is_account_group_member('{ADMIN_GROUP}')", echo=False).first()[0]
if IS_ADMIN:
    print("⚠️ You are in cpg_bootcamp_admins: the filter does not apply to you, the checks are skipped.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 · Before: what can you see without a filter?

# COMMAND ----------


def visibility() -> dict:
    """table -> (rows you see, sorted list of company_code values you see)."""
    out = {}
    for t in ROW_FILTERED:
        r = run(f"SELECT count(*) AS n, sort_array(collect_set({ACCESS_COLUMN})) AS v FROM {C}.{t}", echo=False).first()
        out[t] = (r.n, list(r.v))
    return out


for t, (n, vals) in visibility().items():
    print(f"{t:40} {n:>7,} rows   {ACCESS_COLUMN}: {', '.join(vals)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 · Mapping table: your user id → `company_code`
# MAGIC
# MAGIC One row per user and market they may see (`ALL` = everything). The cell makes **your** rows equal
# MAGIC to the widget. Giving a colleague access later means inserting a row here - no code change.

# COMMAND ----------

run(f"""CREATE TABLE IF NOT EXISTS {G}.{ACCESS_TABLE} (
  user_email STRING NOT NULL COMMENT 'User id as current_user() returns it (compared case-insensitively)',
  {ACCESS_COLUMN} STRING NOT NULL COMMENT 'company_code the user may see, or ALL'
) COMMENT 'Row-level access: which markets each user may see. Read by governance.{FILTER_FN}().'""")

have = {r[0] for r in run(f"SELECT {ACCESS_COLUMN} FROM {G}.{ACCESS_TABLE} WHERE lower(user_email) = lower(:u)",
                          {"u": USER_ID}, echo=False).collect()}
if have == set(ACCESS):
    print(f"unchanged: {USER_ID} -> {ACCESS}")
else:
    run(f"DELETE FROM {G}.{ACCESS_TABLE} WHERE lower(user_email) = lower(:u)", {"u": USER_ID})
    for v in ACCESS:
        run(f"INSERT INTO {G}.{ACCESS_TABLE} VALUES (:u, :v)", {"u": USER_ID, "v": v})
    CHANGES.append(f"mapping {USER_ID}")
display(run(f"SELECT * FROM {G}.{ACCESS_TABLE} ORDER BY user_email, {ACCESS_COLUMN}", echo=False))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 · The row-filter function
# MAGIC
# MAGIC A row filter is a SQL function that gets the row's `company_code` and returns TRUE when the row may be
# MAGIC shown: when **your user id** (`current_user()`) is mapped to that value or to `ALL`, or you are an admin.
# MAGIC
# MAGIC The mapping table itself is never filtered: a policy function must not read a table that has a policy itself.

# COMMAND ----------

BODY = f"""is_account_group_member('{ADMIN_GROUP}')
  OR EXISTS (SELECT 1 FROM {G}.{ACCESS_TABLE} a
             WHERE lower(a.user_email) = lower(current_user())
               AND a.{ACCESS_COLUMN} IN ('ALL', {FILTER_FN}.{ACCESS_COLUMN}))"""
exists = run(f"SELECT count(*) FROM {C}.information_schema.routines "
             f"WHERE routine_schema = 'governance' AND routine_name = '{FILTER_FN}'", echo=False).first()[0] > 0
if exists:
    print(f"unchanged: function governance.{FILTER_FN}")
else:
    run(f"""CREATE FUNCTION {G}.{FILTER_FN}({ACCESS_COLUMN} STRING) RETURNS BOOLEAN
COMMENT 'Row filter: TRUE if the current user may see this {ACCESS_COLUMN} (governance.{ACCESS_TABLE}).'
RETURN {BODY}""")
    CHANGES.append(f"function {FILTER_FN}")
display(run(f"SELECT v AS {ACCESS_COLUMN}, {G}.{FILTER_FN}(v) AS i_may_see_it "
            f"FROM (SELECT DISTINCT {ACCESS_COLUMN} AS v FROM {C}.silver.{ROW_FILTERED[0].split('.')[1]}) ORDER BY v",
            echo=False))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5 · Attach the row filter to the `company_code` column
# MAGIC
# MAGIC `ALTER MATERIALIZED VIEW <table> SET ROW FILTER governance.company_filter ON (company_code)` - the gold tables
# MAGIC are pipeline materialized views. The filter survives pipeline refreshes, and a change to the mapping table
# MAGIC works immediately. Only gold is filtered: it is the serving layer; consumers never get `SELECT` on silver.

# COMMAND ----------

attached_now = {f"{r.table_schema}.{r.table_name}" for r in run(
    f"SELECT table_schema, table_name FROM {C}.information_schema.row_filters", echo=False).collect()}
attached = []
for t in ROW_FILTERED:
    if t in attached_now:
        attached.append((t, "unchanged"))
        continue
    run(f"{alter(t)} SET ROW FILTER {G}.{FILTER_FN} ON ({ACCESS_COLUMN})")
    attached.append((t, "attached"))
    CHANGES.append(f"row filter on {t}")
display(spark.createDataFrame(attached, "gold_table string, row_filter string"))
display(run(f"SELECT table_schema, table_name, filter_name, target_columns FROM {C}.information_schema.row_filters"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6 · After: the same query again
# MAGIC
# MAGIC You now see exactly the markets you are mapped to. No error: the other rows simply do not exist for you.

# COMMAND ----------

# every value that exists, from the unfiltered silver tables (correct on a re-run, when gold is already filtered)
ALL_VALUES = {t: set(run(f"SELECT collect_set({ACCESS_COLUMN}) FROM {C}.silver.{t.split('.')[1]}", echo=False).first()[0])
              for t in ROW_FILTERED}
for t, (n, seen) in visibility().items():
    want = ALL_VALUES[t] if "ALL" in ACCESS else ALL_VALUES[t] & set(ACCESS)
    print(f"{t:40} {n:>7,} rows   {ACCESS_COLUMN}: {', '.join(seen) or 'none'}")
    if not IS_ADMIN:
        check(f"{t} shows exactly {sorted(want)}", set(seen) == want and (n > 0) == bool(want))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7 · The metric view inherits the filter
# MAGIC
# MAGIC A metric view reads the filtered gold table **as you**, so it returns only your markets. Genie does the
# MAGIC same: it runs every query as the person who asks. Govern once, use everywhere.
# MAGIC
# MAGIC Try it: set `company_code` to `ALL` (or another value) and run the notebook again - this cell changes with it.

# COMMAND ----------

display(run("SELECT country_code, MEASURE(gmv_eur) AS gmv_eur, MEASURE(orders) AS orders FROM __C__.consumer.dtc_sales_metrics WHERE order_year = 2026 GROUP BY ALL ORDER BY country_code".replace("__C__", C)))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8 · *(optional)* Rollback, and summary
# MAGIC
# MAGIC With `rollback = true` the row filter, the function and the mapping table are removed again (the data stays).

# COMMAND ----------

if ROLLBACK:
    for t in ROW_FILTERED:
        run(f"{alter(t)} DROP ROW FILTER")
    run(f"DROP FUNCTION IF EXISTS {G}.{FILTER_FN}")
    run(f"DROP TABLE IF EXISTS {G}.{ACCESS_TABLE}")
    left = run(f"SELECT count(*) FROM {C}.information_schema.row_filters WHERE table_schema = '{SAMPLE}'",
               echo=False).first()[0]
    check("rollback: no row filters left", left == 0, f"{left} left")

display(spark.createDataFrame(CHECKS or [("no checks run", "-", "")], "check string, result string, detail string"))
failed = [c for c in CHECKS if c[1] == "FAIL"]
print(f"{len(CHECKS) - len(failed)} PASS, {len(failed)} FAIL; changed now: {CHANGES or 'nothing (re-run)'}")
dbutils.notebook.exit(json.dumps({"catalog": CATALOG, "user_id": USER_ID, "access": ACCESS, "checks": len(CHECKS),
                                  "failed": len(failed), "changes": CHANGES, "rolled_back": ROLLBACK}))
