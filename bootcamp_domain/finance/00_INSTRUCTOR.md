# Instructor guide - Finance sample (simplified)

For instructors who run the [Finance sample](README.md) as a workshop. The instructor notebook prepares the
**Finance domain only**; the rest of a workshop's prerequisites are listed below.

## 1. Pre-event checklist

| item | where | done by |
|---|---|---|
| governed tags, the domain **Finance** with its sub-domains `Finance/General Ledger` and `Finance/Receivables Payables` (published), `ASSIGN` for the participants group | [`01_notebooks/00_instructor_setup.py`](01_notebooks/00_instructor_setup.py) | you |
| account groups `cpg_bootcamp_participants` (participants) and `cpg_bootcamp_admins` (instructors, bypass policies) | your IdP or account console | account admin |
| **CAN USE** on a serverless SQL warehouse for every participant | the warehouse's *Permissions* | workspace admin |
| catalogs `genie_finance_<short name>`, or `CREATE CATALOG` for participants | participants create them in notebook 01 | metastore admin |
| serverless compute; the repository as a Git folder (public, or a Git credential per user) | workspace settings | workspace admin |
| previews *Discover*, *tags on Genie Agents*, *MCP tools in Genie Agents* | Admin settings → Previews | workspace admin |
| one rehearsal of steps 1-5 as a **non-admin** participant | [README](README.md) | you |

## 2. Running `00_instructor_setup.py`

Attach **Serverless** and **Run all**. Everything it creates is read from [`05_context/`](05_context/)
(`_domain.md` and the two `_subdomain.md` files).

| widget | default | meaning |
|---|---|---|
| `mode` | `setup` | `teardown_domain` after the event |
| `dry_run` | `false` | `true` = check only |
| `confirm_teardown` | blank | teardown deletes only when this equals `teardown_domain` |
| `participants_group` | `cpg_bootcamp_participants` | gets ASSIGN on the domain tags (not created here) |
| `tag_prefix` | blank | `zz_test_` when testing (participants then set the same prefix in notebook 05) |

| step | what |
|---|---|
| 2 | admin check, account id |
| 3 | Domains API reachable; the *Discover* and *tags on Genie Agents* previews |
| 4 | governed tag `Finance` and one per sub-domain, the domain and its sub-domains, published |
| 5 | ASSIGN on those tags for the participants group |
| 6 | all tags of the domain, and where participants applied them (re-run during the workshop to follow progress) |

A `Finance` domain that already exists - for example from the full bootcamp - is reused, and missing
sub-domains are added under it.

## 3. During the workshop

| symptom | fix |
|---|---|
| notebook 05: governed tags missing | this notebook has not run, ran as a dry run, or with a `tag_prefix` |
| notebook 05: no permission to assign a tag | participant not in `cpg_bootcamp_participants`, or step 5 reported `ACTION` |
| a participant still sees everything after notebook 03 | they are in `cpg_bootcamp_admins`, or chose `ALL` |
| everything else | the troubleshooting table of the [README](README.md) |

## 4. After the workshop

1. Participants run `01_notebooks/99_cleanup.py` (dropping a catalog removes its tags).
2. Run `00_instructor_setup.py` with `mode = teardown_domain` (first run = dry run), then with
   `confirm_teardown = teardown_domain`. It deletes only the tags and domains it created (marker
   `[created by genie_bootcamp_diggibyte/bootcamp_domain/finance/00_instructor_setup]`).
