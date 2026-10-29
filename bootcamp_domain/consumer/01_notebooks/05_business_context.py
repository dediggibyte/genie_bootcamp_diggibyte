# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 05 · Business context — the Consumer domain, its sub-domains and Pages
# MAGIC
# MAGIC Your agent knows **what the data is** (comments, keys, metric views) and **who may see what** (notebook 03).
# MAGIC It still needs **what the business means**: what counts as GMV, why cancelled orders never count, who is an active shopper. Fjällmark keeps that as code in this sample's
# MAGIC folder `05_context/`:
# MAGIC
# MAGIC | file | becomes |
# MAGIC |---|---|
# MAGIC | `_domain.md` | the UC Semantics **domain** `Consumer` (a governed tag) |
# MAGIC | `<subdomain>/_subdomain.md` (2) | its **sub-domains** `Consumer/<Sub-domain>`, and which tables belong to each |
# MAGIC | `pages/*.md` (3) + `glossary.csv` | one **Page** per business term |
# MAGIC
# MAGIC The domain and sub-domain tags are created once per account by the instructor (`00_instructor_setup`).
# MAGIC **This notebook files your own assets into them:**
# MAGIC
# MAGIC | step | what |
# MAGIC |---|---|
# MAGIC | 1 | parameters; read `05_context/` |
# MAGIC | 2 | check that the governed tags exist (if not, steps 3-5 are skipped - steps 6-7 still run) |
# MAGIC | 3 | tag the **`consumer` schema** with the domain, every **table and metric view** with its sub-domain |
# MAGIC | 4 | tag your **Genie Agent** with the domain |
# MAGIC | 5 | **verify** in `information_schema` |
# MAGIC | 6 | **Pages**: the *Bulk import pages* prompt for Genie Code (UI) |
# MAGIC | 7 | **GitHub MCP** click-path for your agent, and draft your own Page |
# MAGIC
# MAGIC ▶ Serverless → **Run all**. `action = remove` takes the tags off again. 🔁 Re-running only sets what is missing.

# COMMAND ----------

import csv
import html
import json
import os
import re
import unicodedata
from urllib.parse import quote

from databricks.sdk import WorkspaceClient
from databricks.sdk.errors import DatabricksError, NotFound

SAMPLE = "consumer"
GITHUB_REPO = "dediggibyte/genie_bootcamp_diggibyte"
dbutils.widgets.text("catalog", "", "Catalog (blank = automatic)")
dbutils.widgets.text("tag_prefix", "", "Tag prefix (only if the instructor used one)")
dbutils.widgets.dropdown("action", "apply", ["apply", "remove"], "Action")


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


def front_matter(path: str) -> dict:
    """Tiny YAML front-matter reader: 'key: value' lines only."""
    with open(path, encoding="utf-8") as fh:
        m = re.match(r"^---\n(.*?)\n---", fh.read(), re.S)
    out = {}
    for line in (m.group(1).splitlines() if m else []):
        k, sep, v = line.partition(":")
        if sep and not line.startswith(" ") and v.strip():
            out[k.strip()] = v.strip().strip('"')
    return out


w = WorkspaceClient()
host = w.config.host.rstrip("/")
user_name = spark.sql("SELECT current_user()").first()[0]
catalog = dbutils.widgets.get("catalog").strip() or f"genie_{SAMPLE}_{bundle_short_name(user_name)}"
action = dbutils.widgets.get("action")
prefix = dbutils.widgets.get("tag_prefix")
BUNDLE_ROOT = bundle_root()
CONTEXT_DIR = f"{BUNDLE_ROOT}/05_context"

DOMAIN_TAG = prefix + front_matter(f"{CONTEXT_DIR}/_domain.md")["domain_tag"]
OBJECT_TAG = {}   # table or metric view -> sub-domain tag
SUBDOMAINS = []
for folder in sorted(os.listdir(CONTEXT_DIR)):
    path = f"{CONTEXT_DIR}/{folder}/_subdomain.md"
    if os.path.isfile(path):
        fm = front_matter(path)
        tag = prefix + fm["subdomain_tag"]
        SUBDOMAINS.append(tag)
        for name in [x.strip() for x in (fm.get("tables", "") + "," + fm.get("metric_views", "")).split(",") if x.strip()]:
            OBJECT_TAG[name] = tag
print(f"Catalog : {catalog}\nAction  : {action}\nDomain  : {DOMAIN_TAG}")
display(spark.createDataFrame(sorted((t, o) for o, t in OBJECT_TAG.items()), "subdomain_tag string, object string"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 · Do the governed tags exist?
# MAGIC
# MAGIC Only a **governed** tag (one with a tag policy) defines a domain. Unity Catalog would accept an ungoverned tag
# MAGIC with the same name, but it would never show up in Discover - so we check first. Missing? Ask the instructor
# MAGIC to run `01_notebooks/00_instructor_setup.py`, or create the domain under **Discover → Domains**.

# COMMAND ----------


def rest(method: str, path: str, body: dict = None, query: dict = None):
    return w.api_client.do(method, path, body=body, query=query)


missing = []
for key in [DOMAIN_TAG] + SUBDOMAINS:
    try:
        rest("GET", f"/api/2.1/tag-policies/{quote(key, safe='')}")
    except NotFound:
        missing.append(key)
    except DatabricksError as e:
        if "not found" in str(e).lower():
            missing.append(key)
tags_ready = not (missing and action == "apply")
print("✅ all governed tags exist." if not missing else
      f"⚠️ governed tags missing: {missing} - steps 3-5 are skipped; steps 6-7 still run.")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 · Tag the schema, its tables and metric views
# MAGIC
# MAGIC Domain tags are **value-less**: `ALTER SCHEMA ... SET TAGS ('Consumer')`. A schema tag is inherited by
# MAGIC every table in it; a sub-domain tag is not inherited, so each table gets its own. Gold tables use
# MAGIC `ALTER TABLE` (works on pipeline materialized views), metric views `ALTER VIEW`.

# COMMAND ----------


def q(*parts: str) -> str:
    return ".".join("`" + p.replace("`", "``") + "`" for p in parts)


def run(stmt: str):
    try:
        spark.sql(stmt)
        return f"{verb} OK"
    except Exception as e:
        msg = str(e).split("\n")[0]
        return msg + ("  -> you need ASSIGN on this governed tag" if "PERMISSION" in msg.upper() else "")


verb = "SET" if action == "apply" else "UNSET"
results = []
if not tags_ready:
    print("Skipped - governed tags missing (step 2).")
else:
    have_schema = {r.tag_name for r in spark.sql(
        f"SELECT tag_name FROM {q(catalog)}.information_schema.schema_tags WHERE schema_name = '{SAMPLE}'").collect()}
    have_table = {(r.table_name, r.tag_name) for r in spark.sql(
        f"SELECT table_name, tag_name FROM {q(catalog)}.information_schema.table_tags WHERE schema_name = '{SAMPLE}'").collect()}
    if (DOMAIN_TAG in have_schema) == (action == "apply"):
        results.append((SAMPLE, "SCHEMA", DOMAIN_TAG, "already as wanted"))
    else:
        results.append((SAMPLE, "SCHEMA", DOMAIN_TAG, run(f"ALTER SCHEMA {q(catalog, SAMPLE)} {verb} TAGS ('{DOMAIN_TAG}')")))
    for r in spark.sql(f"SELECT table_name, table_type FROM {q(catalog)}.information_schema.tables "
                       f"WHERE table_schema = '{SAMPLE}'").collect():
        tag = OBJECT_TAG.get(r.table_name)
        if not tag:
            continue
        kind = "VIEW" if r.table_type in ("VIEW", "METRIC_VIEW") else "TABLE"
        if ((r.table_name, tag) in have_table) == (action == "apply"):
            results.append((r.table_name, r.table_type, tag, "already as wanted"))
        else:
            results.append((r.table_name, r.table_type, tag,
                            run(f"ALTER {kind} {q(catalog, SAMPLE, r.table_name)} {verb} TAGS ('{tag}')")))
    display(spark.createDataFrame(results, "object string, type string, tag string, result string"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 · Tag your Genie Agent with the domain
# MAGIC Genie Agents are workspace objects: they are tagged with the entity-tag-assignments API (Beta). Only the domain
# MAGIC tag - sub-domain tags (with `/`) cannot be assigned to workspace objects.

# COMMAND ----------

AGENT_TITLE = f"Fjällmark Consumer Analyst ({catalog})"
agent_id, token = None, None
while agent_id is None:
    resp = rest("GET", "/api/2.0/genie/spaces", query={"page_size": 100, **({"page_token": token} if token else {})})
    agent_id = next((s["space_id"] for s in resp.get("spaces", []) if s.get("title") == AGENT_TITLE), None)
    token = resp.get("next_page_token")
    if not token:
        break
agent_result = "no agent yet - run notebook 04 first"
if agent_id and tags_ready:
    try:
        have = {t["tag_key"] for t in rest("GET", f"/api/2.0/entity-tag-assignments/geniespaces/{agent_id}/tags")
                .get("tag_assignments", [])}
    except DatabricksError:
        have = set()
    if (DOMAIN_TAG in have) == (action == "apply"):
        agent_result = "already as wanted"
    else:
        try:
            if action == "apply":
                rest("POST", "/api/2.0/entity-tag-assignments",
                     {"entity_type": "geniespaces", "entity_id": agent_id, "tag_key": DOMAIN_TAG})
            else:
                rest("DELETE", f"/api/2.0/entity-tag-assignments/geniespaces/{agent_id}/tags/{quote(DOMAIN_TAG, safe='')}")
            agent_result = f"{verb} OK"
        except DatabricksError as e:
            agent_result = f"FAILED: {str(e)[:200]}"
print(f"{AGENT_TITLE}: {agent_result}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5 · Verify
# MAGIC Expected after `apply`: the schema carries `Consumer`, every table and metric view exactly one sub-domain tag.

# COMMAND ----------

ok = False
if tags_ready:
    tag_list = ", ".join(f"'{t}'" for t in [DOMAIN_TAG] + SUBDOMAINS)
    n_schema = spark.sql(f"SELECT count(*) FROM {q(catalog)}.information_schema.schema_tags "
                         f"WHERE schema_name = '{SAMPLE}' AND tag_name IN ({tag_list})").first()[0]
    tagged = spark.sql(f"""SELECT tag_name, array_join(sort_array(collect_list(table_name)), ', ') AS objects
                           FROM {q(catalog)}.information_schema.table_tags
                           WHERE schema_name = '{SAMPLE}' AND tag_name IN ({tag_list}) GROUP BY tag_name""")
    display(tagged)
    n_objects = spark.sql(f"SELECT count(*) FROM {q(catalog)}.information_schema.table_tags "
                          f"WHERE schema_name = '{SAMPLE}' AND tag_name IN ({tag_list})").first()[0]
    want = (1, len(OBJECT_TAG)) if action == "apply" else (0, 0)
    ok = (n_schema, n_objects) == want
    print(f"schema tagged: {n_schema}, objects tagged: {n_objects} (expected {want}) ->", "✅ OK" if ok else "⚠️ check above")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6 · Import the glossary as Pages (Genie Code *Bulk import pages*, UI)
# MAGIC
# MAGIC Pages have no API yet; the **Bulk import pages** mode of Genie Code in the Page editor creates them from files you
# MAGIC attach. The cell writes the prompt with your catalog and the workspace paths filled in:
# MAGIC
# MAGIC 1. **Discover → Pages → Create page**, open the Genie Code pane, choose **Bulk import pages**.
# MAGIC 2. **+ → Add context**: add the `pages` folder and `glossary.csv` (paths below).
# MAGIC 3. Paste the prompt, review the proposed Pages (sub-domain of each!) and let Genie Code create them as **drafts**.
# MAGIC
# MAGIC Drafts are visible only to you (and curators); Genie One uses them in your own conversations.

# COMMAND ----------

glossary_path, pages_dir = f"{CONTEXT_DIR}/glossary.csv", f"{CONTEXT_DIR}/pages"
with open(glossary_path, encoding="utf-8", newline="") as fh:
    terms = list(csv.DictReader(fh))
filing = "; ".join(f"subdomain '{s}' -> '{DOMAIN_TAG}/{s}'" for s in sorted({t["subdomain"] for t in terms}))
prompt = (
    f"Bulk import the Fjällmark business glossary for the domain '{DOMAIN_TAG}'. Use only the attached workspace "
    f"files: the index {glossary_path} and the term pages in {pages_dir}. Create exactly one Page per index row "
    f"({len(terms)} terms: {', '.join(t['term'] for t in terms)}). For each row read the Markdown file named in "
    f"page_path: Page name = title; Synonyms = synonyms; Description = description; Page body = the Markdown after the "
    f"front matter, word for word, with every '<catalog>' replaced by '{catalog}'; Related assets = related_assets "
    f"with '<catalog>' replaced by '{catalog}'; Sources = the single link "
    f"https://github.com/{GITHUB_REPO}/blob/main/bootcamp_domain/{SAMPLE}/05_context/<page_path>. File each Page "
    f"under its sub-domain: {filing}. If a Page with the same name exists, flag it as a duplicate instead of creating "
    f"a second one. Create all Pages as drafts; do not publish.")
rows = "".join(f"<tr><td><input type='checkbox'></td><td>{html.escape(t['term'])}</td>"
               f"<td>{html.escape(t['subdomain'])}</td><td><code>{html.escape(t['page_path'])}</code></td></tr>"
               for t in terms)
displayHTML(f"""<div style="font-family:sans-serif;font-size:14px">
<p>Open <a href="{host}/discover/pages" target="_blank">Discover → Pages</a> → Create page → Genie Code → <b>Bulk import pages</b>.</p>
<p><b>Add context</b>:<br><code>{html.escape(pages_dir)}</code><br><code>{html.escape(glossary_path)}</code></p>
<p><b>Prompt</b>:</p>
<pre style="white-space:pre-wrap;user-select:all;background:#f4f4f4;border:1px solid #ccc;padding:10px;max-width:1100px">{html.escape(prompt)}</pre>
<p><b>Expected Pages</b> (drafts):</p>
<table border="1" cellpadding="4" style="border-collapse:collapse"><tr><th>✓</th><th>Page</th><th>sub-domain</th><th>file</th></tr>{rows}</table>
</div>""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 7 · Give your agent the glossary (GitHub MCP), then draft your own Page
# MAGIC
# MAGIC MCP sources work in **Agent mode** only, and every call runs with **your** GitHub account. A private repository
# MAGIC needs the Databricks GitHub connector app installed by a GitHub organisation admin.
# MAGIC
# MAGIC **Your turn - draft a Page:** Discover → Pages → Create page; pick a term that is not defined yet (e.g.
# MAGIC *Repeat purchase rate*, *Basket size* or *Loyalty penetration*); copy the structure of a file in `05_context/pages/` (definition → rules → SQL → pitfalls →
# MAGIC example questions); add your tables under *Related assets*; **save as draft**; ask Genie One and check that it
# MAGIC cites your Page. **Never put personal data in a Page** - Pages are account-level.

# COMMAND ----------

mcp_description = (
    f"Business glossary of Fjällmark Consumer Goods, domain {DOMAIN_TAG}. Before you answer a question that uses a "
    f"business term ({', '.join(t['term'] for t in terms)} ...), read the matching file in the GitHub repository "
    f"{GITHUB_REPO}, folder bootcamp_domain/{SAMPLE}/05_context/pages/ (index: bootcamp_domain/{SAMPLE}/05_context/"
    f"glossary.csv), and follow its rules and calculation. Read only; never create issues, branches or pull requests.")
print(f"""1. Open your agent: {f'{host}/genie/rooms/{agent_id}' if agent_id else '(run notebook 04 first)'}
2. Switch to Agent mode -> Configure -> Sources -> Add -> MCP services -> system.ai.github, sign in to GitHub
3. Paste as the source description:

{mcp_description}

4. Switch off the write tools. Ask: "According to our glossary, what is an active shopper - and how many do we have?"
""")
dbutils.notebook.exit(json.dumps({"catalog": catalog, "action": action, "governed_tags_missing": missing,
                                  "tagged": len(results), "agent": agent_result, "pages": len(terms), "ok": ok}))
