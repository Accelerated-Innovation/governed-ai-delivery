# Marts — The Public Contract

**Authority:**
- `docs/data/architecture/BOUNDARIES.md`
- `docs/data/architecture/MODEL_LAYERING.md` (stack overlay)
- `docs/data/architecture/PIPELINE_CONTRACT.md` — ownership + exposure rules

Marts are what downstream consumers (BI, services, reverse-ETL) read. Treat
the column list as a public API.

## Rules

- Reads from `intermediate/` or other `marts/` only — never staging, never
  raw warehouse, never sources directly
- Materialization: `table` (small) or `incremental` (large; requires a
  documented unique key + ADR if new)
- Naming: `dim_*` (dimension), `fct_*` (fact), or domain-shaped
  (`customer_360`)
- Primary key: `unique` + `not_null` tests required (per
  `DATA_QUALITY_CONTRACT.md`)
- Every column described in `_<model>.yml`

## Exposures

Every mart consumed by a downstream system MUST have an exposure entry in
`models/marts/_exposures.yml` declaring:
- Type (dashboard / application / notebook / ml)
- Owner (team + email)
- Description ≥ 1 sentence on what the consumer does with the data

A mart without an exposure entry is either dead code (delete) or
undocumented (add the entry).

## Breaking changes

| Change | Required |
|---|---|
| Add a new column | Code review (additive; safe) |
| Add a new mart | Code review + downstream sign-off if any consumer named |
| Remove a column | ADR + deprecation period (≥ 1 release cycle) + consumer notification |
| Rename a column | Same as remove + add |
| Change a column's semantics (same name, different meaning) | ADR — the worst kind of change; avoid |
| Add a row-filter that excludes previously-included rows | ADR + downstream sign-off |

## PII at the mart boundary

A mart that exposes individual-level PII columns:
- Tags every PII column in `_<model>.yml`
- Has an exposure entry naming the consumer + business case
- Is reviewed quarterly per `PII_HANDLING_CONTRACT.md`

Aggregate marts (no individual-level PII) have no such restrictions.

## Anti-patterns

- A mart with `select *` (breaks downstream on schema changes)
- A mart with no exposure entry (undocumented contract)
- A mart referenced only by other marts (might be intermediate; review)
- A mart that filters silently (e.g., `where is_test_account = false`
  without documenting in description)
- A new mart shipped without consumer sign-off
