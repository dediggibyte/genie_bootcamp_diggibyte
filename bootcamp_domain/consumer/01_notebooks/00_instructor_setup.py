# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # 00 · Instructor setup - Consumer domain (admins only, once before the event)
# MAGIC
# MAGIC Prepares the **Consumer domain** for this sample: the governed tags, the UC Semantics domain with its two
# MAGIC sub-domains, and the permission for participants to *assign* those tags (their notebook 05 applies them).
# MAGIC Everything is read from this sample's `05_context/` folder (`_domain.md`, `*/_subdomain.md`).
# MAGIC
# MAGIC | step | what | needs |
# MAGIC |---|---|---|
# MAGIC | 2 | who am I: admin check, account id | workspace admin |
# MAGIC | 3 | prerequisites: Domains API, *Discover* and *tags on Genie Agents* previews | workspace admin |
# MAGIC | 4 | **governed tags + domain** `Consumer` and its sub-domains, published | CREATE on governed tags |
# MAGIC | 5 | the participants group may **ASSIGN** the tags | MANAGE on the governed tags |
# MAGIC | 6 | **all tags of the domain**: definitions, and where participants applied them | |
# MAGIC | T | **teardown** after the event (`mode = teardown_domain`) | same |
# MAGIC
# MAGIC Not here: account groups, catalogs, warehouse permissions (see `00_INSTRUCTOR.md`).
# MAGIC
# MAGIC ▶ Serverless → **Run all** (`dry_run = true` for a check-only run). 🔁 Re-running reuses what exists.
# MAGIC
# MAGIC **Teardown removes only what this notebook created** (marker in the description). A `Consumer` domain that
# MAGIC already existed - for example from the full bootcamp - is reused and kept.
# MAGIC
# MAGIC > Domains and governed tags are **account-level**. Testing? Use `tag_prefix = zz_test_` and tear down afterwards.

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1 · Parameters
# MAGIC
# MAGIC | widget | default | meaning |
# MAGIC |---|---|---|
# MAGIC | `mode` | `setup` | `teardown_domain` after the event |
# MAGIC | `dry_run` | `false` | `true` = only check and report |
# MAGIC | `confirm_teardown` | blank | teardown deletes only when this equals `teardown_domain` |
# MAGIC | `participants_group` | `cpg_bootcamp_participants` | account group that gets ASSIGN (not created here) |
# MAGIC | `tag_prefix` | blank | prefix for every tag key (`zz_test_` when testing) |

# COMMAND ----------

import json
import os
import re
import urllib.parse

from databricks.sdk import WorkspaceClient

SAMPLE = "consumer"
dbutils.widgets.dropdown("mode", "setup", ["setup", "teardown_domain"], "1 Mode")
dbutils.widgets.dropdown("dry_run", "false", ["true", "false"], "2 Dry run")
dbutils.widgets.text("confirm_teardown", "", "3 Teardown: type teardown_domain")
dbutils.widgets.text("participants_group", "cpg_bootcamp_participants", "4 Participants group")
dbutils.widgets.text("tag_prefix", "", "5 Tag prefix (zz_test_ when testing)")

MODE = dbutils.widgets.get("mode")
DRY_RUN = dbutils.widgets.get("dry_run") == "true"
if MODE != "setup" and not DRY_RUN and dbutils.widgets.get("confirm_teardown").strip() != MODE:
    DRY_RUN = True
    print("Teardown guard: confirm_teardown is not 'teardown_domain' - this run is a DRY RUN.\n")
GROUP = dbutils.widgets.get("participants_group").strip()
PREFIX = dbutils.widgets.get("tag_prefix")
MARKER = f"[created by genie_bootcamp_diggibyte/bootcamp_domain/{SAMPLE}/00_instructor_setup]"
CHECKLIST = []
w = WorkspaceClient()
me = spark.sql("SELECT current_user()").first()[0]


def record(area: str, item: str, status: str, detail: str = "") -> None:
    CHECKLIST.append((area, item, status, detail))
    print(f"[{status:7s}] {area:10s} | {item}" + (f"  -- {detail}" if detail else ""))


def act(area: str, item: str, fn, detail: str = ""):
    """Run fn() unless dry run, or a setup change while in teardown mode."""
    if MODE != "setup" and area != "teardown":
        return record(area, item, "SKIP", "teardown mode")
    if DRY_RUN:
        return record(area, item, "DRY-RUN", detail or "would be changed")
    try:
        result = fn()
        record(area, item, "DONE", detail)
        return result
    except Exception as e:
        record(area, item, "ERROR", str(e).splitlines()[0][:300])


def api(method: str, path: str, query: dict = None, body: dict = None):
    return w.api_client.do(method, path, query=query, body=body)


def list_all(path: str, key: str) -> list:
    items, token = [], None
    while True:
        resp = api("GET", path, query={"page_size": 100, **({"page_token": token} if token else {})})
        items += resp.get(key, [])
        token = resp.get("next_page_token")
        if not token:
            return items


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
    with open(path, encoding="utf-8") as fh:
        m = re.match(r"^---\n(.*?)\n---", fh.read(), re.S)
    out = {}
    for line in (m.group(1).splitlines() if m else []):
        k, sep, v = line.partition(":")
        if sep and not line.startswith(" ") and v.strip():
            out[k.strip()] = v.strip().strip('"')
    return out


CONTEXT_DIR = f"{bundle_root()}/05_context"
fm = front_matter(f"{CONTEXT_DIR}/_domain.md")
ROOT_KEY = PREFIX + fm["domain_tag"]
PLAN = [(ROOT_KEY, None, fm["subtitle"], fm["description"])]          # (tag key, parent, subtitle, description)
for folder in sorted(os.listdir(CONTEXT_DIR)):
    if os.path.isfile(f"{CONTEXT_DIR}/{folder}/_subdomain.md"):
        s = front_matter(f"{CONTEXT_DIR}/{folder}/_subdomain.md")
        PLAN.append((PREFIX + s["subdomain_tag"], ROOT_KEY, f"{fm['domain_tag']} - {s['subdomain']}", s["description"]))
ICON, COLOR = "ADDRESS_BOOK", "#1565C0"
print(f"Instructor: {me}\nMode: {MODE.upper()} - {'DRY RUN' if DRY_RUN else 'APPLY'}")
for key, parent, *_ in PLAN:
    print(("    " if parent else "") + key)


def in_scope(key: str) -> bool:
    return key == ROOT_KEY or key.startswith(ROOT_KEY + "/")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2 · Who am I?

# COMMAND ----------

is_admin = spark.sql("SELECT is_member('admins')").first()[0]
record("identity", f"{me} is a workspace admin", "OK" if is_admin else "ERROR")
groups = api("GET", "/api/2.0/identity/groups", query={"page_size": 1}).get("groups", [])
account_id = groups[0]["account_id"] if groups else None     # needed for governed-tag permissions
record("identity", "account id", "OK" if account_id else "WARN", account_id or "unknown")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Teardown *(only when `mode = teardown_domain`)*
# MAGIC Deletes sub-domains, the domain and the governed tags that carry this notebook's marker, then stops. Run it
# MAGIC after participants ran notebook 99.

# COMMAND ----------

if MODE != "setup":
    domains = list_all("/api/2.0/domains", "domains")
    ours = {d["tag_key"] for d in domains if in_scope(d["tag_key"]) and MARKER in (d.get("description") or "")}
    deleted = set()
    for d in sorted((d for d in domains if in_scope(d["tag_key"])), key=lambda d: d["tag_key"] == ROOT_KEY):
        children = {c["tag_key"] for c in domains if c["tag_key"].startswith(d["tag_key"] + "/")}
        if d["tag_key"] not in ours or children - ours:
            record("teardown", f"domain '{d['tag_key']}'", "KEEP", "not created by this notebook, or has foreign sub-domains")
        else:
            deleted.add(d["tag_key"])
            act("teardown", f"delete domain '{d['tag_key']}'", lambda i=d["domain_id"]: api("DELETE", f"/api/2.0/domains/{i}"))
    still_used = {d["tag_key"] for d in domains} - deleted
    for t in sorted(list_all("/api/2.1/tag-policies", "tag_policies"), key=lambda t: t["tag_key"] == ROOT_KEY):
        if not in_scope(t["tag_key"]):
            continue
        if MARKER not in (t.get("description") or "") or t["tag_key"] in still_used:
            record("teardown", f"governed tag '{t['tag_key']}'", "KEEP", "not ours, or still used by a domain")
        else:
            act("teardown", f"delete governed tag '{t['tag_key']}'",   # '/' must be encoded as %2F
                lambda k=t["tag_key"]: api("DELETE", f"/api/2.1/tag-policies/{urllib.parse.quote(k, safe='')}"))
    display(spark.createDataFrame([list(c) for c in CHECKLIST], "area string, item string, status string, detail string"))
    dbutils.notebook.exit(json.dumps({"mode": MODE, "dry_run": DRY_RUN, "checklist": CHECKLIST}))

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3 · Prerequisites
# MAGIC The notebook reads the previews; it does not change them (Admin settings → Previews).

# COMMAND ----------

try:
    n = len(api("GET", "/api/2.0/domains").get("domains", []))
    record("domains", "Domains API (Beta) reachable", "OK", f"{n} domain(s) in the account")
except Exception as e:
    record("domains", "Domains API (Beta) reachable", "ERROR", str(e).splitlines()[0])
for name, why in {"discover_page": "Discover page (Domains, Pages)",
                  "enable_lakeview_tags": "tags on Genie Agents"}.items():
    try:
        v = api("GET", f"/api/2.1/settings/{name}")
        on = bool((v.get("effective_boolean_val") or v.get("boolean_val") or {}).get("value"))
    except Exception:
        on = False
    record("settings", f"{name} ({why})", "OK" if on else "ACTION", "" if on else "enable it in Admin settings > Previews")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4 · Governed tags and the Consumer domain
# MAGIC
# MAGIC A domain *is* a governed tag. Order matters: (1) the governed tag (a tag policy without values), (2) the
# MAGIC domain with `tag_key` = that tag (created as draft), (3) a sub-domain needs its own tag `<domain>/<Sub-domain>`
# MAGIC and `parent_domain_id`, (4) publish with `PATCH ...?update_mask=draft`.

# COMMAND ----------

tag_policies = {t["tag_key"]: t for t in list_all("/api/2.1/tag-policies", "tag_policies")}
domains = {d["tag_key"]: d for d in list_all("/api/2.0/domains", "domains")}
for key, parent, subtitle, description in PLAN:
    kind = "sub-domain" if parent else "domain"
    if key in tag_policies:
        record("tags", f"governed tag '{key}'", "OK", "exists")
    else:
        created = act("tags", f"create governed tag '{key}'", lambda k=key, d=description: api(
            "POST", "/api/2.1/tag-policies", body={"tag_key": k, "description": f"{d[:170]} {MARKER}"}))
        if created:
            tag_policies[key] = created
    if key in domains:
        record("domains", f"{kind} '{key}'", "OK", "exists")
    else:
        parent_id = domains.get(parent, {}).get("domain_id") if parent else None
        if parent and not parent_id:
            record("domains", f"{kind} '{key}'", "DRY-RUN" if DRY_RUN else "ERROR", "parent domain missing")
            continue
        body = {"tag_key": key, "draft": True, "subtitle": subtitle[:120], "description": f"{description} {MARKER}",
                "icon": {"name": ICON, "color": COLOR}, **({"parent_domain_id": parent_id} if parent_id else {})}
        created = act("domains", f"create {kind} '{key}'", lambda b=body: api("POST", "/api/2.0/domains", body=b))
        if created:
            domains[key] = created
    d = domains.get(key)
    if d and d.get("effective_draft", d.get("draft", True)):
        updated = act("domains", f"publish '{key}'", lambda i=d["domain_id"]: api(
            "PATCH", f"/api/2.0/domains/{i}", query={"update_mask": "draft"}, body={"draft": False}))
        if updated:
            domains[key] = updated

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5 · Let participants ASSIGN the tags
# MAGIC Applying a governed tag needs `APPLY TAG` on the object (participants own their catalog) **and** `ASSIGN` on
# MAGIC the tag: role `roles/tagPolicy.assigner` on `accounts/<id>/tagPolicies/<id>/ruleSets/default`.

# COMMAND ----------

principal = f"groups/{GROUP}"
group = next((g for g in api("GET", "/api/2.0/identity/groups", query={"filter": f'group_name eq "{GROUP}"'})
              .get("groups", []) if g.get("group_name") == GROUP), None)
if not group:
    record("tag-perms", f"group {GROUP}", "ACTION", "group not found - create it, then re-run")
ASSIGN = {}
for key, *_ in PLAN:
    policy = tag_policies.get(key)
    if not (group and policy and account_id):
        ASSIGN[key] = "-"
        continue
    name = f"accounts/{account_id}/tagPolicies/{policy['id']}/ruleSets/default"
    rule_set = api("GET", "/api/2.0/preview/accounts/access-control/rule-sets", query={"name": name, "etag": ""})
    rules = rule_set.get("grant_rules", [])
    if any(r.get("role") == "roles/tagPolicy.assigner" and principal in r.get("principals", []) for r in rules):
        ASSIGN[key] = "yes"
        record("tag-perms", f"ASSIGN on '{key}' for {GROUP}", "OK", "already granted")
        continue
    new_rules = [dict(r) for r in rules]
    assigner = next((r for r in new_rules if r.get("role") == "roles/tagPolicy.assigner"), None)
    if assigner:
        assigner["principals"] = sorted(set(assigner.get("principals", [])) | {principal})
    else:
        new_rules.append({"role": "roles/tagPolicy.assigner", "principals": [principal]})
    done = act("tag-perms", f"grant ASSIGN on '{key}' to {GROUP}", lambda n=name, e=rule_set.get("etag"), r=new_rules: api(
        "PUT", "/api/2.0/preview/accounts/access-control/rule-sets",
        body={"name": n, "rule_set": {"name": n, "etag": e, "grant_rules": r}}))
    ASSIGN[key] = "yes" if done else "no"

# COMMAND ----------

# MAGIC %md
# MAGIC ## 6 · All tags of the domain
# MAGIC Definitions, then where the tags are applied (`system.information_schema`, only catalogs **you** can see -
# MAGIC ask participants for `USE CATALOG` + `BROWSE` to follow their progress). Empty until they run notebook 05.

# COMMAND ----------

tag_policies = {t["tag_key"]: t for t in list_all("/api/2.1/tag-policies", "tag_policies")}
domains = {d["tag_key"]: d for d in list_all("/api/2.0/domains", "domains")}
display(spark.createDataFrame(
    [(k, "sub-domain" if p else "domain", "yes" if k in tag_policies else "missing",
      "missing" if k not in domains else ("draft" if domains[k].get("effective_draft") else "published"),
      ASSIGN.get(k, "-")) for k, p, *_ in PLAN],
    "tag_key string, kind string, governed_tag string, domain_state string, participants_assign string"))
display(spark.sql("""
    SELECT 'schema' AS level, catalog_name, schema_name, CAST(NULL AS STRING) AS table_name, tag_name
    FROM system.information_schema.schema_tags WHERE tag_name = :root OR startswith(tag_name, concat(:root, '/'))
    UNION ALL
    SELECT 'table', catalog_name, schema_name, table_name, tag_name
    FROM system.information_schema.table_tags WHERE tag_name = :root OR startswith(tag_name, concat(:root, '/'))
    ORDER BY catalog_name, level, schema_name, table_name""", {"root": ROOT_KEY}))

# COMMAND ----------

summary = spark.createDataFrame([list(c) for c in CHECKLIST], "area string, item string, status string, detail string")
display(summary)
print("Dry run - nothing changed." if DRY_RUN else "Done.",
      "After the event: mode = teardown_domain, confirm_teardown = teardown_domain.")
dbutils.notebook.exit(json.dumps({"sample": SAMPLE, "mode": MODE, "dry_run": DRY_RUN, "checklist": CHECKLIST}))
