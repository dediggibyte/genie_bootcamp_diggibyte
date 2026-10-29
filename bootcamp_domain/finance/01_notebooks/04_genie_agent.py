# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 04 · Your Genie Agent — the Finance Analyst
# MAGIC
# MAGIC Steps 1-3 gave you **governed data**: gold tables, metric views with the official KPI definitions and a row
# MAGIC filter. Now you put a **Genie Agent** (formerly *Genie space*) on top, so the business can
# MAGIC ask questions in plain language - and you can **prove** the answers are right with benchmarks.
# MAGIC
# MAGIC The agent is kept as code in `04_genie/fjallmark_finance_analyst.json` (a serialized Genie space with
# MAGIC `__CATALOG__` instead of your catalog name):
# MAGIC
# MAGIC | building block | in this template |
# MAGIC |---|---|
# MAGIC | data sources | 4 gold tables + 2 metric view(s) |
# MAGIC | column settings | synonyms, entity matching on categorical columns, personal columns hidden |
# MAGIC | text instruction | company, calendar, currency, privacy + the finance business rules |
# MAGIC | example SQL, SQL snippets | trusted query patterns |
# MAGIC | sample questions | 3 starter questions |
# MAGIC | benchmarks | 5 questions with a checked SQL answer - the agent's test suite |
# MAGIC
# MAGIC | step | what |
# MAGIC |---|---|
# MAGIC | 1 | parameters: catalog, SQL warehouse |
# MAGIC | 2 | check that every data source exists |
# MAGIC | 3 | build the agent for your catalog from the template |
# MAGIC | 4 | create the agent, or update it in place |
# MAGIC | 5 | ask a test question (Conversation API) |
# MAGIC | 6 | run the benchmarks (evaluation API) |
# MAGIC | 7 | share it, and attach the glossary with the GitHub MCP (UI) |
# MAGIC
# MAGIC 🔁 **Re-running is safe.** The agent is found by its title; if its template version is unchanged nothing is
# MAGIC written, so your edits in the Genie UI survive. Steps 5 and 6 only read.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 · Parameters
# MAGIC
# MAGIC | widget | default | meaning |
# MAGIC |---|---|---|
# MAGIC | `catalog` | blank = `genie_finance_<short name>` | your catalog |
# MAGIC | `warehouse` | blank = first serverless warehouse you can use | SQL warehouse id or name |
# MAGIC | `ask_test_question` / `run_benchmarks` | `true` | steps 5 and 6 on / off |
# MAGIC | `force_update` | `false` | `true` overwrites the agent with the template (discards UI edits) |

# COMMAND ----------

import json
import os
import time
import unicodedata

import pandas as pd
from databricks.sdk import WorkspaceClient

SAMPLE = "finance"
TEMPLATE_FILE = f"04_genie/fjallmark_{SAMPLE}_analyst.json"
PLACEHOLDER = "__CATALOG__"
TEST_QUESTION = "What were net revenue and gross margin by quarter in 2026?"

dbutils.widgets.text("catalog", "", "1 Catalog (blank = automatic)")
dbutils.widgets.text("warehouse", "", "2 SQL warehouse id or name (blank = automatic)")
dbutils.widgets.dropdown("ask_test_question", "true", ["true", "false"], "3 Ask a test question")
dbutils.widgets.dropdown("run_benchmarks", "true", ["true", "false"], "4 Run the benchmarks")
dbutils.widgets.dropdown("force_update", "false", ["false", "true"], "5 Force update from template")


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
    raise FileNotFoundError("databricks.yml not found above this notebook - run it from the Git folder.")


w = WorkspaceClient()
host = w.config.host.rstrip("/")
user_name = w.current_user.me().user_name
catalog = dbutils.widgets.get("catalog").strip() or f"genie_{SAMPLE}_{bundle_short_name(user_name)}"
BUNDLE_ROOT = bundle_root()


def pick_warehouse(wanted: str) -> dict:
    whs = w.api_client.do("GET", "/api/2.0/sql/warehouses").get("warehouses", [])
    if wanted:
        for wh in whs:
            if wanted in (wh["id"], wh["name"]):
                return wh
        raise ValueError(f"SQL warehouse '{wanted}' not found (or you have no permission on it).")
    serverless = sorted((wh for wh in whs if wh.get("enable_serverless_compute")),
                        key=lambda wh: (wh["name"] != "Serverless Starter Warehouse", wh.get("state") != "RUNNING", wh["name"]))
    if not serverless:
        raise ValueError("No serverless SQL warehouse visible to you - ask an admin for CAN USE on one.")
    return serverless[0]


warehouse = pick_warehouse(dbutils.widgets.get("warehouse").strip())
print(f"You are   : {user_name}\nCatalog   : {catalog}\nWarehouse : {warehouse['name']} ({warehouse['id']})")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 · Does your catalog have every data source?
# MAGIC Genie refuses to create an agent on a table that does not exist. If something is missing, run the bundle job
# MAGIC `genie_finance_job` (step 2) first.

# COMMAND ----------

with open(f"{BUNDLE_ROOT}/{TEMPLATE_FILE}", encoding="utf-8") as fh:
    template = json.load(fh)
existing = {f"{r.table_schema}.{r.table_name}": r.table_type for r in spark.sql(
    f"SELECT table_schema, table_name, table_type FROM `{catalog}`.information_schema.tables "
    f"WHERE table_schema = '{SAMPLE}'").collect()}
sources = template["serialized_space"]["data_sources"]
rows = [(kind, s["identifier"].replace(f"{PLACEHOLDER}.", ""))
        for kind, key in (("table", "tables"), ("metric view", "metric_views")) for s in sources.get(key, [])]
check = pd.DataFrame([(k, f"{catalog}.{n}", existing.get(n, "MISSING")) for k, n in rows],
                     columns=["kind", "object", "found as"])
display(check)
if (check["found as"] == "MISSING").any():
    raise RuntimeError(f"Data sources missing in {catalog} - run the bundle job genie_{SAMPLE}_job first.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 · Build the agent definition for your catalog
# MAGIC Notice that the benchmark questions are **not** among the example SQLs: benchmarks test an agent, they must
# MAGIC not teach it the answers.

# COMMAND ----------

space_json = json.dumps(template["serialized_space"], ensure_ascii=False).replace(PLACEHOLDER, catalog)
space = json.loads(space_json)
version_tag = f"[template {template['template_version']}]"
title = f"{template['title']} ({catalog})"
description = f"{template['description']} Catalog: {catalog}. {version_tag}"
tricky = set(template.get("tricky_benchmark_ids", []))
print(f"{title}: {len(space['data_sources']['tables'])} tables, {len(space['data_sources']['metric_views'])} metric views, "
      f"{len(space['instructions']['example_question_sqls'])} example SQLs, {len(space['benchmarks']['questions'])} benchmarks\n")
print("".join(space["instructions"]["text_instructions"][0]["content"]))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 · Create or update the agent
# MAGIC
# MAGIC | situation | call |
# MAGIC |---|---|
# MAGIC | no agent with this title | `POST /api/2.0/genie/spaces` (in your home folder) |
# MAGIC | same template version and warehouse | nothing |
# MAGIC | template changed, or `force_update = true` | `PATCH /api/2.0/genie/spaces/<id>` - same id, same link |

# COMMAND ----------


def list_spaces() -> list:
    out, token = [], None
    while True:
        resp = w.api_client.do("GET", "/api/2.0/genie/spaces",
                               query={"page_size": 100, **({"page_token": token} if token else {})})
        out += resp.get("spaces", [])
        token = resp.get("next_page_token")
        if not token:
            return out


body = {"warehouse_id": warehouse["id"], "title": title, "description": description, "serialized_space": space_json}
match = next((s for s in list_spaces() if s.get("title") == title), None)
if not match:
    space_id = w.api_client.do("POST", "/api/2.0/genie/spaces",
                               body={**body, "parent_path": f"/Workspace/Users/{user_name}"})["space_id"]
    action = "created"
else:
    space_id = match["space_id"]
    detail = w.api_client.do("GET", f"/api/2.0/genie/spaces/{space_id}")
    if (version_tag in (detail.get("description") or "") and detail.get("warehouse_id") == warehouse["id"]
            and dbutils.widgets.get("force_update") != "true"):
        action = "unchanged"
    else:
        w.api_client.do("PATCH", f"/api/2.0/genie/spaces/{space_id}", body=body)
        action = "updated"
url = f"{host}/genie/rooms/{space_id}"
print(f"{title}: {action} ({space_id})")
displayHTML(f'<p style="font-size:16px">👉 <a href="{url}" target="_blank">Open "{title}" in Genie</a></p>')

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5 · Ask a test question (Conversation API)
# MAGIC `start-conversation`, poll the message until `COMPLETED`, read the SQL and fetch the rows. This is how you embed
# MAGIC an agent in an app or test it automatically. **Read the SQL** - does it use the metric view?

# COMMAND ----------


def ask_genie(question: str, timeout_s: int = 300):
    start = w.api_client.do("POST", f"/api/2.0/genie/spaces/{space_id}/start-conversation", body={"content": question})
    base = f"/api/2.0/genie/spaces/{space_id}/conversations/{start['conversation_id']}/messages/{start['message_id']}"
    deadline, m = time.time() + timeout_s, {}
    while time.time() < deadline:
        m = w.api_client.do("GET", base)
        if m.get("status") in ("COMPLETED", "FAILED", "CANCELLED", "QUERY_RESULT_EXPIRED"):
            break
        time.sleep(4)
    text, sql, df = [], None, None
    for a in m.get("attachments") or []:
        if a.get("text"):
            text.append(a["text"].get("content", ""))
        if a.get("query"):
            sql = a["query"].get("query", "")
            res = w.api_client.do("GET", f"{base}/attachments/{a['attachment_id']}/query-result")
            sr = res.get("statement_response", {})
            cols = [c["name"] for c in sr.get("manifest", {}).get("schema", {}).get("columns", [])]
            df = pd.DataFrame(sr.get("result", {}).get("data_array", []) or [], columns=cols)
    return m.get("status", "TIMEOUT"), "\n".join(text), sql, df


if dbutils.widgets.get("ask_test_question") == "true":
    status, text, sql, df = ask_genie(TEST_QUESTION)
    print(f"Q: {TEST_QUESTION}\nstatus: {status}\nGenie: {text}\nSQL:\n{sql}")
    if df is not None:
        display(df)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6 · Run the benchmarks (evaluation API)
# MAGIC
# MAGIC Genie answers every benchmark question, runs its own SQL and the checked SQL, and grades the result:
# MAGIC `GOOD` (same result), `BAD` (`reasons` says why) or `NEEDS_REVIEW`. The run also appears in the agent's
# MAGIC **Benchmarks → Evaluations** tab. Benchmarks marked ⚠ are deliberately tricky - when one fails, compare
# MAGIC `genie_sql` with `expected_sql`, improve the agent (instruction, example, synonym) and run this step again.
# MAGIC
# MAGIC 🔐 Genie runs as **you**: with the step 3 defaults some benchmarks return only your rows. The expected values
# MAGIC in the sample README are for a user who sees everything.

# COMMAND ----------

FINAL = {"DONE", "EVALUATION_FAILED", "EVALUATION_CANCELLED", "EVALUATION_TIMEOUT"}
score = None
if dbutils.widgets.get("run_benchmarks") == "true":
    api = f"/api/2.0/genie/spaces/{space_id}/eval-runs"
    run = w.api_client.do("POST", api, body={})          # no ids = all benchmarks
    run_id, started = run["eval_run_id"], time.time()
    while run.get("eval_run_status") not in FINAL and time.time() - started < 1800:
        time.sleep(15)
        run = w.api_client.do("GET", f"{api}/{run_id}")
        print(f"  {run.get('eval_run_status')} {run.get('num_done', 0)}/{run.get('num_questions', '?')}")
    results, token = [], None
    while True:
        resp = w.api_client.do("GET", f"{api}/{run_id}/results",
                               query={"page_size": 100, **({"page_token": token} if token else {})})
        results += resp.get("eval_results", [])
        token = resp.get("next_page_token")
        if not token:
            break
    sql_of = lambda rs: "\n;\n".join(r.get("response", "") for r in rs or [] if r.get("response_type") == "SQL")  # noqa: E731
    rows = []
    for r in results:
        d = w.api_client.do("GET", f"{api}/{run_id}/results/{r['result_id']}")
        rows.append({"question": ("⚠ " if r.get("benchmark_question_id") in tricky else "") + (r.get("question") or ""),
                     "assessment": d.get("assessment") or "NEEDS_REVIEW",
                     "reasons": ", ".join(d.get("assessment_reasons") or []),
                     "genie_sql": sql_of(d.get("actual_response")), "expected_sql": sql_of(d.get("expected_response"))})
    bench = pd.DataFrame(rows)
    good = int((bench["assessment"] == "GOOD").sum()) if len(bench) else 0
    score = f"{good}/{len(bench)} GOOD"
    print(f"Benchmark score: {score} (run {run_id}, {run.get('eval_run_status')})")
    if len(bench):
        display(bench.sort_values(["assessment", "question"]))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7 · Share it - and give it the glossary (UI)
# MAGIC
# MAGIC **Share:** open the agent → **Share** → a user or group → **Can run**. The viewer also needs `CAN USE` on the
# MAGIC warehouse and `SELECT` on the gold schema `finance` (never on bronze or silver). Their answers respect
# MAGIC **their** row filter - you configured security once, in Unity Catalog.
# MAGIC
# MAGIC **GitHub MCP (Agent mode):** the definitions behind the instructions are the Pages in
# MAGIC `bootcamp_domain/finance/05_context/pages/`. Open the agent → switch to **Agent** → **Configure → Sources →
# MAGIC Add → MCP services → `system.ai.github`**, sign in to GitHub, and use notebook 05's printed description.
# MAGIC Then ask: *"According to our glossary, how is DSO defined - and what is DE01's DSO?"*. MCP sources need the workspace setting *MCP tools in Genie Agents*.
# MAGIC
# MAGIC ✅ Next: notebook `05_business_context` files your schema, tables and this agent into the *Finance* domain.

# COMMAND ----------

dbutils.notebook.exit(json.dumps({"catalog": catalog, "space_id": space_id, "title": title, "action": action,
                                  "url": url, "template_version": template["template_version"], "benchmarks": score}))
