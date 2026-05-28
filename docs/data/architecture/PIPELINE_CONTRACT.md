# Pipeline Contract

This document defines what counts as a "pipeline" in this repository,
who owns it, and the minimum metadata it must carry. Stack-specific
implementation lives in the overlay docs (`TECH_STACK.md`, etc.).

---

# 1. What Is a Pipeline

A pipeline is any scheduled or event-triggered transformation that produces
a named output dataset.

This includes:
- A dbt project run (`dbt build` on a model + its downstream)
- An Airflow / Dagster / Prefect DAG
- A scheduled notebook (rare; flag for review)
- A Spark / Beam job

A pipeline is NOT:
- An ad-hoc analyst query (one-off; not scheduled)
- A BI dashboard refresh (separate tool surface)
- A source-system internal job (not in our control)

---

# 2. Required Metadata

Every pipeline declares:
- **id** — kebab-case, unique within the repo (`customer_dim_daily`)
- **owner** — team email or individual; not "data team" (too vague)
- **schedule** — cron or human-readable (`0 6 * * *` or "daily 06:00 UTC")
- **inputs** — sources or upstream pipelines it depends on
- **outputs** — datasets / marts it produces (the contract)
- **freshness SLA** — how stale outputs may be before alerting (see
  `DATA_QUALITY_CONTRACT.md`)
- **alert recipient** — where failures land (Slack channel, PagerDuty service)

Storage of this metadata varies per stack:
- dbt: `models/*_<model>.yml` + `models/marts/_exposures.yml` + `dbt_project.yml`
- Airflow: in the DAG file (`default_args`, `doc_md`, `owner`)
- Dagster: `@asset` / `@job` decorators with metadata

---

# 3. Pipeline Lifecycle

| Stage | Owner action |
|---|---|
| **New** | PR with all required metadata; sign-off from a peer + downstream owner if a new mart |
| **Active** | Scheduled refresh, alerts firing; metadata kept current |
| **Deprecated** | `description:` marked `[DEPRECATED]`; sunset date declared; downstream consumers notified |
| **Removed** | Pipeline + outputs deleted; ADR documents the decision; lineage tools updated |

A pipeline left in "no consumer + no owner + no recent run" state for
> 90 days is auto-flagged for deprecation review by `govkit doctor` (planned).

---

# 4. Failure Modes + Response

| Failure | Expected response |
|---|---|
| Source freshness breach | Alert source owner; don't block the dbt run |
| Schema test `error` | Block the affected mart's refresh; alert owner |
| Cost spike (>2× rolling 7-day median) | Alert oncall; investigate before next run |
| Lineage tool ingestion failure | Alert team; lineage is documentation, not blocking |

---

# 5. Inter-Pipeline Dependencies

When pipeline A feeds pipeline B:
- B's input includes A's output dataset
- B's schedule allows for A's worst-case completion time (with margin)
- B's freshness SLA accounts for A's freshness SLA (cascade)

For complex DAGs, use the orchestrator's dependency mechanism rather than
schedule offsets. Schedule-offset coordination breaks during backfills.

---

# 6. Per-Environment Behavior

Per `ENVIRONMENTS.md`:
- `dev` pipelines run on demand; no scheduled refresh
- `ci` pipelines run on PR + main push; ephemeral schema per PR
- `staging` runs on schedule; same code as prod, smaller compute
- `prod` runs on schedule; alerts wired to oncall

The pipeline definition is environment-agnostic; the schedule + target
schema + alerting are environment-specific.
