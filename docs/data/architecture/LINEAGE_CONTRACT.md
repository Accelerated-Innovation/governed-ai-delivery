# Lineage Contract

This document defines what lineage must be captured and how long it's
retained. Stack-specific tooling (dbt manifest, OpenLineage, Datahub)
lives in the overlay's `LINEAGE_OBSERVABILITY.md`.

---

# 1. What Must Be Captured

| Granularity | When | Storage |
|---|---|---|
| **Source → mart** (dataset-level) | Every CI run + every prod run | Lineage tool (dbt Cloud, Datahub, OpenLineage, etc.) |
| **Model → model** (DAG edges) | Every CI run + every prod run | Same |
| **Column lineage** (which source columns feed which mart columns) | Every prod run | Same; required for PII-tagged columns |
| **Exposure** (mart → BI dashboard / app) | On change | `exposures.yml` or equivalent |
| **Run history** (when did pipeline X last succeed) | Every run | Warehouse audit table OR observability tool |

---

# 2. Retention

| Artifact | Minimum retention |
|---|---|
| dbt artifacts (manifest, run_results) | 30 days |
| Lineage records (in the lineage tool) | 90 days |
| Run history (warehouse audit table) | 1 year |
| Exposure definitions | Indefinite (versioned in git) |

Teams in regulated environments may need longer retention — document the
override in an ADR.

---

# 3. PII + Lineage

Column-level lineage is REQUIRED for every PII-tagged column. The lineage
tool must answer: "if a customer requests deletion, which marts contain
their PII?"

The mechanism varies per stack:
- dbt: `meta.contains_pii: true` propagated through staging → marts; lineage
  tool reads `manifest.json` and inherits tags
- Custom pipelines: explicit annotation in pipeline metadata + ingestion script

---

# 4. Discoverability

Anyone on the team should be able to answer:
1. "What feeds this mart?" — via lineage tool's upstream view
2. "What breaks if I change this mart?" — via lineage tool's downstream view
3. "Who owns this dataset?" — via exposures + dataset metadata
4. "When did this last refresh successfully?" — via run history table

If any of these takes more than 2 minutes, the lineage infrastructure
needs work, not the user.

---

# 5. Incident Use

When a data-quality alert fires, the lineage tool is the first stop:
1. Identify all downstream marts of the affected source/model
2. Identify all exposures touching those marts
3. Notify the owners of those exposures
4. Decide: pause refreshes vs ship a hotfix

A lineage tool that's stale at this moment is a process failure — fix the
ingestion job's reliability before the next incident.

---

# 6. When Lineage Is Optional

For exploratory/sandbox work in `dev`:
- Lineage capture is nice-to-have, not required
- Models in `dev_*` schemas can lack `_<model>.yml` files

For production marts: lineage capture is non-negotiable. A mart shipping
without lineage capture is a regression and a CI failure (planned as a
future doctor check, D015+).
