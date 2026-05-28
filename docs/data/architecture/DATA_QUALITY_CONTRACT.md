# Data Quality Contract

This document defines what data quality means in this repository — what
tests exist, what severity they carry, and what gates block deploys.

Stack-specific test syntax lives in the overlay's `TESTING.md`. This file
defines the contract that all stacks honor.

---

# 1. Test Tiers

| Tier | What it catches | Severity | Blocks merge? |
|---|---|---|---|
| **Schema** (unique, not_null, accepted_values, FK) | Structural violations | `error` | YES |
| **Custom singular** (project-specific invariants) | Business rules | `error` | YES |
| **Distribution** (row counts, value ranges, quantiles) | Anomalies | `warn` (default) → `error` after stabilization | Only on `error` |
| **Source freshness** | Upstream staleness | `warn` | NO (alert only) |
| **Cost** (run duration, credits) | Resource regressions | `warn` | NO (oncall watches) |

The schema + custom-singular tier is the **floor** — every model must
ship with primary-key uniqueness + non-null at minimum.

---

# 2. When Tests Block Merge

A test failure at `error` severity blocks merge of the PR that touches
the model OR any upstream model in its lineage.

CI selection (per the overlay's `TESTING.md`): `dbt build --select
state:modified+` then `dbt test --select state:modified+`. The `+`
suffix means "this model + all downstream models" so a change to a
staging model exercises every mart that depends on it.

`warn` severity test failures do NOT block merge; they surface in the
PR summary for reviewer judgment.

---

# 3. Promoting Distribution Tests from `warn` to `error`

Distribution tests start `warn` because thresholds are easy to mis-calibrate.

Promote to `error` only when:
- The threshold has held for ≥ 2 weeks of production runs
- An owner is named in the test description ("contact analytics-eng on breach")
- The blast radius is bounded (a single mart, not the whole DAG)

Document the rationale in the test's `description:` field.

---

# 4. Test Coverage Floor

Every model:
- Primary key column: `unique` + `not_null` (or equivalent in non-dbt stacks)
- Description present
- Owner declared at the project / layer level

Every mart additionally:
- All FK columns: `relationships` test pointing at the source dimension
- An exposure entry if consumed by a downstream system

---

# 5. Source Freshness

Every source feeding a daily-or-faster mart declares a freshness contract
(warn_after, error_after). Freshness failures alert the source owner; they
do NOT block the dbt run (the source's staleness is not the dbt PR
requester's fault).

If freshness alerts fire repeatedly for a source, raise an ADR: either
escalate to the source owner, change the SLA, or remove the dependency.

---

# 6. When to Skip a Test

Skipping a test (`severity: warn` downgrade from `error`, or `--exclude` in
CI) requires an ADR. Ad-hoc skips create cumulative tech debt; every
skipped test is a future incident.

Acceptable skip patterns:
- During a documented backfill window (skip + restore in same PR)
- For a deprecated mart being phased out (skip + delete in same release)
- For a new test still in calibration (start `warn`, see §3)

---

# 7. Quality Beyond Tests

Tests catch what they're written for. Distribution drift in unflagged
columns, latent quality issues in long-tail data, and semantic regressions
(metric definition shifts) need additional discipline:

- Periodic data audits (manual or scripted) for high-value marts
- Owner sign-off on new metrics + metric changes
- Documented assumptions in mart descriptions ("excludes test customers
  per `where is_test_account = false`")

These belong in `BOUNDARIES.md` (what's in scope of which mart) and the
team's calibration cadence — not in dbt tests.
