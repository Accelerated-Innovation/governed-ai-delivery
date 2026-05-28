# Data Quality — Test Discipline

**Authority:**
- `docs/data/architecture/DATA_QUALITY_CONTRACT.md` — test tiers + severity
- `docs/data/architecture/TESTING.md` (stack overlay) — stack-specific HOW

This rule fires when editing any model or test file.

## Test floor (non-negotiable)

Every model ships with:
- Primary key: `unique` + `not_null` (severity `error`)
- Every column declared in `_<model>.yml` with a description
- Tests on FK columns: `relationships` pointing at the parent dim

## Severity policy

| Tier | Severity | Blocks merge? |
|---|---|---|
| Schema (unique, not_null, accepted_values, relationships) | `error` | YES |
| Custom singular (project-specific invariants) | `error` | YES |
| Distribution (`dbt-expectations`, row counts, value ranges) | `warn` (default) → `error` after ≥ 2 weeks stable | Only on `error` |
| Source freshness | `warn` | NO (alert only) |

A distribution test promoted to `error` must have:
- An owner named in `description:`
- A note explaining the calibration source ("based on Q1 2026 baseline")
- Bounded blast radius (single mart, not the whole DAG)

## Skipping a test

Severity downgrade or `--exclude` in CI requires an ADR. Acceptable cases:
- Documented backfill window (skip + restore in same PR)
- Deprecated mart phase-out (skip + delete in same release)
- Distribution test still in calibration (`warn` is the floor, not skip)

## When to ADD a custom singular test

When the invariant doesn't fit a column-level test. Example: "every order
in `fct_orders` has a corresponding customer in `dim_customers`" needs a
custom test, not just `relationships` (which only checks FK validity, not
NULL handling at the join).

Custom tests live in `tests/` and return only the rows that violate the
invariant. Empty result = test passes.

## Anti-patterns

- A schema test marked `warn` "because it sometimes flakes" (fix the flake,
  not the severity)
- A new model shipped with no tests at all
- A distribution test that's been `warn` for 6 months — either promote
  to `error` or delete it (the threshold isn't real if no one acts on it)
- Skipping `--select state:modified+` in CI (full-build is slow; selective
  build catches the same regressions cheaper)
