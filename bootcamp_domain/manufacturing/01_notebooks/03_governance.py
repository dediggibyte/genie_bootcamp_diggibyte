# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 03 · Governance — who may see which plant, and who may see sensitive data
# MAGIC
# MAGIC Your gold tables are built, and right now **everybody who can read them sees everything**: the production orders of every plant, every actual production cost and the names of shift supervisors.
# MAGIC In this notebook you put one Unity Catalog **row filter** and 2 **column mask(s)** on the gold
# MAGIC tables. Because the policies live *on the tables*, every consumer inherits them: SQL, dashboards, the
# MAGIC metric views and the **Genie Agent** of notebook 04.
# MAGIC
# MAGIC | step | what |
# MAGIC |---|---|
# MAGIC | 1-2 | parameters, pre-flight check |
# MAGIC | 3 | **before**: what you see without policies |
# MAGIC | 4 | **mapping tables**: *who may see what* is data, not code |
# MAGIC | 5 | **functions**: one row filter, the column masks |
# MAGIC | 6 | **attach** them to the gold tables |
# MAGIC | 7 | **after**: the same queries again, with checks |
# MAGIC | 8 | **switch persona** by editing the mapping - the effect is immediate |
# MAGIC | 9 | the **metric view inherits** the policies |
# MAGIC | 10 | **try to break it** |
# MAGIC | 11 | *(optional)* rollback, summary |
# MAGIC
# MAGIC ▶ **How to run:** Serverless → **Run all**. Every statement is printed above its result.
# MAGIC
# MAGIC 🔁 **Re-running is a no-op**: mapping rows, functions and policies that are already in place are reported
# MAGIC as `unchanged`.
# MAGIC
# MAGIC > Members of the account group `cpg_bootcamp_admins` bypass every policy. Test as a non-admin.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 · Parameters
# MAGIC
# MAGIC | widget | default | meaning |
# MAGIC |---|---|---|
# MAGIC | `catalog` | blank = `genie_manufacturing_<short name>` | your catalog |
# MAGIC | `user_email` | your login | whose access you configure |
# MAGIC | `plant_code` | `SE-LUN` | the plants that user may see: `SE-LUN`, `SE-LUN,PL-POZ` or `ALL` |
# MAGIC | `sensitive_access` | `false` | `true` = that user may read actual production cost and supervisor names in clear text |
# MAGIC | `rollback` | `false` | `true` = remove everything this notebook created at the end (**leave it `false`**) |
# MAGIC
# MAGIC Plants: `SE-LUN` Lund · `SE-NKP` Norrköping · `FI-TMP` Tampere · `PL-POZ` Poznań.

# COMMAND ----------

import hashlib
import json
import textwrap
import unicodedata

current_user = spark.sql("SELECT current_user()").first()[0]
dbutils.widgets.text("catalog", "", "1 Catalog (blank = automatic)")
dbutils.widgets.text("user_email", current_user, "2 User e-mail to configure")
dbutils.widgets.text("plant_code", "SE-LUN", "3 Plant(s): SE-LUN | SE-LUN,PL-POZ | ALL")
dbutils.widgets.dropdown("sensitive_access", "false", ["false", "true"], "4 May read cost and names")
dbutils.widgets.dropdown("rollback", "false", ["false", "true"], "5 Roll back at the end")

SAMPLE = "manufacturing"
ADMIN_GROUP = "cpg_bootcamp_admins"   # members bypass every policy (instructors)
# mapping tables: governance.<ACCESS_TABLE>(user_email, <ACCESS_COLUMN>) and governance.<SENSITIVE_TABLE>(user_email)
ACCESS_TABLE = "user_plant_access"
ACCESS_COLUMN = "plant_code"     # the column every row-filtered table carries
SENSITIVE_TABLE = "sensitive_readers"
FILTER_FN = "plant_filter"
# gold tables that get the row filter on ACCESS_COLUMN
ROW_FILTERED = ['manufacturing.production_order', 'manufacturing.downtime_event']
# (gold table, column) -> mask function
MASKS = {('manufacturing.production_order', 'actual_cost_eur'): 'mask_amount', ('manufacturing.production_order', 'shift_supervisor'): 'mask_name'}
# primary key of each masked table (used by the checks)
PRIMARY_KEY = {'manufacturing.production_order': 'production_order_id'}
# fictional personas: e-mail -> (values, may read sensitive data, who)
PERSONAS = {
    'johan.lindgren@example.com': (['SE-LUN'], True, 'Johan Lindgren, plant manager Lund'),
    'marta.kowalczyk@example.com': (['PL-POZ'], True, 'Marta Kowalczyk, plant controller Poznań'),
    'coo@example.com': (['ALL'], False, 'COO, all plants'),
}


def bundle_short_name(user_name: str) -> str:
    local = user_name.split("@")[0].lower()
    return "".join(c if unicodedata.category(c).startswith("L") or unicodedata.category(c) == "Nd" else "_"
                   for c in local)


CATALOG = dbutils.widgets.get("catalog").strip() or f"genie_{SAMPLE}_{bundle_short_name(current_user)}"
C = f"`{CATALOG}`"
G = f"{C}.governance"
USER_EMAIL = dbutils.widgets.get("user_email").strip() or current_user
ACCESS = sorted({v.strip().upper() for v in dbutils.widgets.get("plant_code").split(",") if v.strip()})
SENSITIVE = dbutils.widgets.get("sensitive_access") == "true"
ROLLBACK = dbutils.widgets.get("rollback") == "true"
CHECKS, CHANGES = [], []

print(f"You are              : {current_user}")
print(f"Catalog              : {CATALOG}")
print(f"Configure access for : {USER_EMAIL} -> {ACCESS_COLUMN} {', '.join(ACCESS)}, sensitive data: {SENSITIVE}")


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
               {"s": schema, "t": name}, echo=False).first()[0]
    return f"ALTER {'MATERIALIZED VIEW' if kind == 'MATERIALIZED_VIEW' else 'TABLE'} {C}.{table}"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 · Pre-flight check
# MAGIC The governed tables must exist (job `genie_manufacturing_job` from step 2 has run).

# COMMAND ----------

have = {f"{r.table_schema}.{r.table_name}" for r in run(
    f"SELECT table_schema, table_name FROM {C}.information_schema.tables WHERE table_schema = '{SAMPLE}'",
    echo=False).collect()}
missing = sorted((set(ROW_FILTERED) | {t for t, _ in MASKS}) - have)
if missing:
    raise RuntimeError(f"Missing gold tables {missing} - run the bundle job genie_{SAMPLE}_job first (step 2).")
IS_ADMIN = run(f"SELECT is_account_group_member('{ADMIN_GROUP}')", echo=False).first()[0]
print("✅ gold tables found." + ("\n⚠️ You are in cpg_bootcamp_admins: the policies do not apply to you, the "
                                  "after-checks are skipped." if IS_ADMIN else ""))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 · Before: what can you see without policies?

# COMMAND ----------


def visibility() -> dict:
    """table -> (rows you see, sorted list of plant_code values you see)."""
    out = {}
    for t in ROW_FILTERED:
        r = run(f"SELECT count(*) AS n, sort_array(collect_set({ACCESS_COLUMN})) AS v FROM {C}.{t}", echo=False).first()
        out[t] = (r.n, list(r.v))
    return out


def clear_text() -> dict:
    """(table, column) -> (rows with a value, rows where gold shows the same value as the ungoverned silver)."""
    out = {}
    for (t, column) in MASKS:
        schema, name = t.split(".")
        k = PRIMARY_KEY[t]
        r = run(f"""SELECT count(s.{column}) AS n, count_if(g.{column} = s.{column}) AS clear
                    FROM {C}.{t} g JOIN {C}.silver.{name} s ON s.{k} = g.{k}""", echo=False).first()
        out[(t, column)] = (r.n, r.clear)
    return out


BEFORE = visibility()
for t, (n, vals) in BEFORE.items():
    print(f"{t:40} {n:>7,} rows   {ACCESS_COLUMN}: {', '.join(vals)}")
for (t, column), (n, clear) in clear_text().items():
    print(f"{t}.{column}: {clear} of {n} values readable in clear text")
display(run("SELECT order_number, plant_code, line_code, actual_cost_eur, shift_supervisor FROM __C__.manufacturing.production_order WHERE order_status = 'completed' ORDER BY production_order_id DESC LIMIT 5".replace("__C__", C), echo=False))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 · Mapping tables: *who may see what* is data
# MAGIC
# MAGIC | table | one row per |
# MAGIC |---|---|
# MAGIC | `governance.user_plant_access` | user and plant they may see (`ALL` = everything) |
# MAGIC | `governance.sensitive_readers` | user who may read actual production cost and supervisor names |
# MAGIC
# MAGIC Three fictional personas are added as well; step 8 *becomes* one of them. Changing access later means
# MAGIC changing a row here - no code, no pipeline run.

# COMMAND ----------

run(f"""CREATE TABLE IF NOT EXISTS {G}.{ACCESS_TABLE} (
  user_email STRING NOT NULL COMMENT 'User e-mail as current_user() returns it (compared case-insensitively)',
  {ACCESS_COLUMN} STRING NOT NULL COMMENT 'plant_code the user may see, or ALL'
) COMMENT 'Row-level access: which plants each user may see. Read by governance.{FILTER_FN}().'""")
run(f"""CREATE TABLE IF NOT EXISTS {G}.{SENSITIVE_TABLE} (
  user_email STRING NOT NULL COMMENT 'User e-mail as current_user() returns it (compared case-insensitively)'
) COMMENT 'Users who may read actual production cost and supervisor names in clear text. Read by governance.can_read_sensitive().'""")


def read_mapping() -> dict:
    """lower(e-mail) -> [set of values, may read sensitive data]"""
    m = {}
    for r in run(f"SELECT lower(user_email) AS e, {ACCESS_COLUMN} AS v FROM {G}.{ACCESS_TABLE}", echo=False).collect():
        m.setdefault(r.e, [set(), False])[0].add(r.v)
    for r in run(f"SELECT lower(user_email) AS e FROM {G}.{SENSITIVE_TABLE}", echo=False).collect():
        m.setdefault(r.e, [set(), False])[1] = True
    return m


MAPPING = read_mapping()


def set_access(email: str, values: list, sensitive: bool) -> None:
    """Make one user's rows equal to (values, sensitive). Writes only what differs."""
    key = email.lower()
    have_v, have_s = MAPPING.get(key, [set(), False])
    if have_v == set(values) and have_s == sensitive:
        print(f"unchanged: {email} -> {sorted(values)}, sensitive {sensitive}")
        return
    if have_v != set(values):
        run(f"DELETE FROM {G}.{ACCESS_TABLE} WHERE lower(user_email) = lower(:e)", {"e": email})
        for v in values:
            run(f"INSERT INTO {G}.{ACCESS_TABLE} VALUES (:e, :v)", {"e": email, "v": v})
    if have_s != sensitive:
        run(f"DELETE FROM {G}.{SENSITIVE_TABLE} WHERE lower(user_email) = lower(:e)", {"e": email})
        if sensitive:
            run(f"INSERT INTO {G}.{SENSITIVE_TABLE} VALUES (:e)", {"e": email})
    MAPPING[key] = [set(values), sensitive]
    CHANGES.append(f"mapping {email}")


for email, (values, sensitive, _) in PERSONAS.items():
    set_access(email, values, sensitive)
set_access(USER_EMAIL, ACCESS, SENSITIVE)
display(spark.createDataFrame([(e, ", ".join(sorted(v)), s) for e, (v, s) in sorted(MAPPING.items())],
                              f"user_email string, {ACCESS_COLUMN} string, may_read_sensitive boolean"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5 · The functions
# MAGIC
# MAGIC | function | kind | returns |
# MAGIC |---|---|---|
# MAGIC | `is_bootcamp_admin()` | helper | TRUE for members of `cpg_bootcamp_admins` |
# MAGIC | `can_read_sensitive()` | helper | TRUE if you are in `governance.sensitive_readers` |
# MAGIC | `plant_filter(plant_code)` | **row filter** | TRUE if you are mapped to that value (or to `ALL`) |
# MAGIC | `mask_amount` | **column mask** on `manufacturing.production_order.actual_cost_eur` | the real amount for sensitive readers, else `NULL` |
# MAGIC | `mask_name` | **column mask** on `manufacturing.production_order.shift_supervisor` | the real name for sensitive readers, else the first letter (`K****`) |
# MAGIC
# MAGIC **Rule:** a policy function must not read a table that has a policy itself (Unity Catalog does not support
# MAGIC *nested* policies). The mapping tables are therefore never governed.

# COMMAND ----------

EXISTING_FNS = {r.routine_name: (r.comment or "") for r in run(
    f"SELECT routine_name, comment FROM {C}.information_schema.routines WHERE routine_schema = 'governance'",
    echo=False).collect()}
OUR_FNS = []


def ensure_function(name: str, params: str, returns: str, comment: str, body: str) -> None:
    """CREATE OR REPLACE only when missing or changed (a fingerprint of the definition sits in the comment)."""
    OUR_FNS.append(name)
    fp = hashlib.sha1("|".join((params, returns, body)).encode()).hexdigest()[:10]
    if EXISTING_FNS.get(name, "").endswith(f"[def {fp}]"):
        print(f"unchanged: function governance.{name}")
        return
    run(f"CREATE OR REPLACE FUNCTION {G}.{name}({params}) RETURNS {returns}\n"
        f"COMMENT '{comment} [def {fp}]'\nRETURN {textwrap.dedent(body).strip()}")
    CHANGES.append(f"function {name}")


ensure_function("is_bootcamp_admin", "", "BOOLEAN", f"TRUE for members of {ADMIN_GROUP}.",
                f"is_account_group_member('{ADMIN_GROUP}')")
ensure_function("can_read_sensitive", "", "BOOLEAN", f"TRUE if the current user is in governance.{SENSITIVE_TABLE}.",
                f"""{G}.is_bootcamp_admin()
                    OR EXISTS (SELECT 1 FROM {G}.{SENSITIVE_TABLE} r WHERE lower(r.user_email) = lower(current_user()))""")
ensure_function(FILTER_FN, f"{ACCESS_COLUMN} STRING", "BOOLEAN",
                f"Row filter: TRUE if the current user may see this {ACCESS_COLUMN} (governance.{ACCESS_TABLE}).",
                f"""{G}.is_bootcamp_admin()
                    OR EXISTS (SELECT 1 FROM {G}.{ACCESS_TABLE} a
                               WHERE lower(a.user_email) = lower(current_user())
                                 AND a.{ACCESS_COLUMN} IN ('ALL', {FILTER_FN}.{ACCESS_COLUMN}))""")
MASK_FUNCTIONS = {
    "mask_email": ("email STRING", "STRING", "Column mask: clear text for sensitive readers, else a***@domain.",
                   f"CASE WHEN {G}.can_read_sensitive() OR email IS NULL THEN email "
                   f"ELSE concat(left(email, 1), '***@', substring_index(email, '@', -1)) END"),
    "mask_name": ("name STRING", "STRING", "Column mask: clear text for sensitive readers, else the first letter.",
                  f"CASE WHEN {G}.can_read_sensitive() OR name IS NULL THEN name ELSE concat(left(name, 1), '****') END"),
    "mask_amount": ("amount DECIMAL(18,2)", "DECIMAL(18,2)", "Column mask: clear amount for sensitive readers, else NULL.",
                    f"CASE WHEN {G}.can_read_sensitive() THEN amount ELSE CAST(NULL AS DECIMAL(18,2)) END"),
}
for fn in sorted(set(MASKS.values())):
    ensure_function(fn, *MASK_FUNCTIONS[fn])

display(run(f"SELECT {G}.can_read_sensitive() AS i_may_read_sensitive", echo=False))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6 · Attach the policies to the gold tables
# MAGIC
# MAGIC `ALTER MATERIALIZED VIEW <t> SET ROW FILTER <fn> ON (<column>)` and `... ALTER COLUMN <c> SET MASK <fn>`.
# MAGIC The policies survive pipeline refreshes, and a change to a mapping row works immediately. Only gold gets
# MAGIC policies: it is the serving layer. Silver stays closed - consumers never get `SELECT` on it (step 10).

# COMMAND ----------

FILTERS_NOW = {f"{r.table_schema}.{r.table_name}": r.filter_name.split(".")[-1].strip("`").lower()
               for r in run(f"SELECT table_schema, table_name, filter_name FROM {C}.information_schema.row_filters",
                            echo=False).collect()}
MASKS_NOW = {(f"{r.table_schema}.{r.table_name}", r.column_name): r.mask_name.split(".")[-1].strip("`").lower()
             for r in run(f"SELECT table_schema, table_name, column_name, mask_name FROM {C}.information_schema.column_masks",
                          echo=False).collect()}
attached = []
for t in ROW_FILTERED:
    if FILTERS_NOW.get(t) == FILTER_FN.lower():
        attached.append((t, "", f"row filter {FILTER_FN}", "unchanged"))
        continue
    run(f"{alter(t)} SET ROW FILTER {G}.{FILTER_FN} ON ({ACCESS_COLUMN})")
    attached.append((t, "", f"row filter {FILTER_FN}", "attached"))
for (t, column), fn in MASKS.items():
    if MASKS_NOW.get((t, column)) == fn:
        attached.append((t, column, f"mask {fn}", "unchanged"))
        continue
    run(f"{alter(t)} ALTER COLUMN {column} SET MASK {G}.{fn}")
    attached.append((t, column, f"mask {fn}", "attached"))
CHANGES += [f"{p} on {t}" for t, _, p, s in attached if s != "unchanged"]
display(spark.createDataFrame(attached, "gold_table string, column string, policy string, result string"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7 · After: the same queries again
# MAGIC
# MAGIC You should now see exactly the plants you are mapped to - no error, the other rows simply do not exist
# MAGIC for you - and masked values unless `sensitive_access = true`.

# COMMAND ----------

# every value that exists, read from the ungoverned silver tables (correct on a re-run, when gold is already filtered)
ALL_VALUES = {t: set(run(f"SELECT collect_set({ACCESS_COLUMN}) FROM {C}.silver.{t.split('.')[1]}", echo=False).first()[0])
              for t in ROW_FILTERED}


def expected(values: list, table: str) -> set:
    return ALL_VALUES[table] if "ALL" in values else ALL_VALUES[table] & set(values)


def verify(values: list, sensitive: bool, label: str) -> None:
    after = visibility()
    for t, (n, seen) in after.items():
        want = expected(values, t)
        check(f"{label}: {t} shows exactly {sorted(want)}", set(seen) == want and (n > 0) == bool(want),
              f"{n:,} rows, {', '.join(seen) or 'none'}")
    for (t, column), (n, clear) in clear_text().items():
        check(f"{label}: {t}.{column} {'readable' if sensitive else 'masked'}",
              clear == n if sensitive else clear == 0, f"{clear} of {n} values in clear text")


if IS_ADMIN:
    print("Admin: policies are bypassed - after-checks skipped.")
elif USER_EMAIL.lower() == current_user.lower():
    verify(ACCESS, SENSITIVE, "you")
else:
    print(f"user_email is {USER_EMAIL}, not you - the checks run as you, so they are skipped.")
display(run("SELECT order_number, plant_code, line_code, actual_cost_eur, shift_supervisor FROM __C__.manufacturing.production_order WHERE order_status = 'completed' ORDER BY production_order_id DESC LIMIT 5".replace("__C__", C), echo=False))

# COMMAND ----------

# MAGIC %md
# MAGIC ### Inspect the policies
# MAGIC Unity Catalog lists every attached policy in `information_schema` (and in Catalog Explorer → table → *Overview*).

# COMMAND ----------

display(run(f"SELECT table_schema, table_name, filter_name, target_columns FROM {C}.information_schema.row_filters"))
display(run(f"SELECT table_schema, table_name, column_name, mask_name FROM {C}.information_schema.column_masks"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 8 · Switch persona: change the mapping, not the code
# MAGIC
# MAGIC | persona | plants | sensitive data |
# MAGIC |---|---|---|
# MAGIC | Johan Lindgren, plant manager Lund (`johan.lindgren@example.com`) | SE-LUN | yes |
# MAGIC | Marta Kowalczyk, plant controller Poznań (`marta.kowalczyk@example.com`) | PL-POZ | yes |
# MAGIC | COO, all plants (`coo@example.com`) | ALL | no |
# MAGIC
# MAGIC The cell copies the mapping of **Marta Kowalczyk, plant controller Poznań** to your e-mail, runs the checks again and then puts
# MAGIC your own mapping back.

# COMMAND ----------

if IS_ADMIN or USER_EMAIL.lower() != current_user.lower():
    print("Skipped (admin, or user_email is not you).")
else:
    p_values, p_sensitive, p_label = PERSONAS["marta.kowalczyk@example.com"]
    print(f"--- you are now: {p_label} ---")
    set_access(current_user, p_values, p_sensitive)
    try:
        verify(p_values, p_sensitive, "persona")
    finally:
        set_access(current_user, ACCESS, SENSITIVE)
        print(f"--- back to your own mapping: {ACCESS}, sensitive {SENSITIVE} ---")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 9 · The metric view inherits the policies
# MAGIC
# MAGIC A metric view reads the governed gold table **as you**, so it returns only your plants. Genie does the
# MAGIC same: it runs every query as the person who asks. Govern once, use everywhere.

# COMMAND ----------

display(run("SELECT plant_code, MEASURE(yield_pct) AS yield_pct, MEASURE(actual_cost_eur) AS actual_cost_eur FROM __C__.manufacturing.production_metrics WHERE finish_year = 2026 GROUP BY ALL ORDER BY plant_code".replace("__C__", C)))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 10 · Try to break it
# MAGIC
# MAGIC | attempt | what happens | lesson |
# MAGIC |---|---|---|
# MAGIC | A · copy the table (`CREATE TABLE ... AS SELECT`) | the copy holds only what *you* see, masked values stay masked - but the copy has **no policy** | give consumers `SELECT` on gold, never `CREATE` on schemas they share; lineage shows every copy |
# MAGIC | B · query silver instead of gold | you see everything - silver has no policies | silver and bronze stay closed: grant consumers only the gold schema |
# MAGIC | C · filter on a hidden value | an empty result, no error | the row does not exist for you - nothing leaks through error messages |

# COMMAND ----------

first = ROW_FILTERED[0]
copy = f"{G}.break_copy_{first.split('.')[1]}"
run(f"CREATE OR REPLACE TABLE {copy} AS SELECT * FROM {C}.{first}")
display(run(f"SELECT '{first} copy' AS attempt, count(*) AS n, sort_array(collect_set({ACCESS_COLUMN})) AS visible FROM {copy}"))
print("Policies on the copy:", run(f"SELECT count(*) FROM {C}.information_schema.row_filters "
                                   f"WHERE table_schema = 'governance'", echo=False).first()[0], "(none - the copy is ungoverned)")
run(f"DROP TABLE {copy}")

display(run(f"SELECT 'silver.{first.split('.')[1]}' AS attempt, count(*) AS n, "
            f"sort_array(collect_set({ACCESS_COLUMN})) AS visible FROM {C}.silver.{first.split('.')[1]}"))

hidden = sorted(ALL_VALUES[first] - expected(ACCESS, first))
if hidden and not IS_ADMIN:
    display(run(f"SELECT '{hidden[0]}' AS asked_for, count(*) AS n FROM {C}.{first} WHERE {ACCESS_COLUMN} = '{hidden[0]}'"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 11 · *(optional)* Rollback, and summary
# MAGIC
# MAGIC With `rollback = true` the policies, the functions and the mapping tables are removed again (the data stays).

# COMMAND ----------

if ROLLBACK:
    for t in ROW_FILTERED:
        run(f"{alter(t)} DROP ROW FILTER")
    for (t, column) in MASKS:
        run(f"{alter(t)} ALTER COLUMN {column} DROP MASK")
    for fn in reversed(OUR_FNS):
        run(f"DROP FUNCTION IF EXISTS {G}.{fn}")
    for table in (ACCESS_TABLE, SENSITIVE_TABLE):
        run(f"DROP TABLE IF EXISTS {G}.{table}")
    left = run(f"SELECT count(*) FROM {C}.information_schema.row_filters WHERE table_schema = '{SAMPLE}'",
               echo=False).first()[0]
    check("rollback: no row filters left", left == 0, f"{left} left")

display(spark.createDataFrame(CHECKS or [("no checks run", "-", "")], "check string, result string, detail string"))
failed = [c for c in CHECKS if c[1] == "FAIL"]
print(f"{len(CHECKS) - len(failed)} PASS, {len(failed)} FAIL; changed now: {CHANGES or 'nothing (re-run)'}")
dbutils.notebook.exit(json.dumps({"catalog": CATALOG, "checks": len(CHECKS), "failed": len(failed),
                                  "changes": CHANGES, "rolled_back": ROLLBACK}))
