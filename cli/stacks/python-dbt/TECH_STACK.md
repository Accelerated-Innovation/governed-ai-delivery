# Technology Stack — Python / dbt

This document defines the approved technology stack for this data repository.

All contributors and AI agents must follow these standards when selecting
adapters, packages, or infrastructure. New technologies require an **ADR**.

---

# 1. Primary Language + Transformation Framework

**SQL + Jinja, orchestrated by dbt-core**

Approved versions:
- `dbt-core ≥ 1.7`
- One warehouse adapter: `dbt-snowflake` / `dbt-bigquery` / `dbt-redshift` /
  `dbt-postgres` / `dbt-databricks`

Rules:
- Models must compile to ANSI-compatible SQL where possible; warehouse-specific
  features require a comment naming the adapter (e.g. `-- snowflake: uses QUALIFY`)
- Jinja logic in models should be data-shape concerns (refs, sources, vars);
  multi-step business logic belongs in an intermediate model, not a macro
- Macros live in `macros/`; one macro per file; documented purpose

---

# 2. Project Layout

Standard dbt project structure:
```
dbt_project/
├── dbt_project.yml
├── packages.yml              # dbt package dependencies (dbt-utils, dbt-expectations, ...)
├── profiles.yml              # NOT committed if it contains credentials
├── models/
│   ├── staging/              # source-shaped, lightly cleaned (renames, type casts)
│   ├── intermediate/         # business-logic transformations (joins, aggregations)
│   └── marts/                # serving layer (consumed by BI / downstream services)
├── tests/                    # custom singular tests
├── macros/                   # reusable Jinja
├── snapshots/                # SCD tracking
└── seeds/                    # reference data
```

The boundary contract:

- `marts/` may NOT read directly from `staging/`; must go through `intermediate/`
  or another mart
- `staging/` must NOT contain joins across sources; it's source-shaped + cleaned
- Cross-mart joins must be documented (lineage gets messy quickly)

See `docs/data/architecture/MODEL_LAYERING.md` for the long form.

---

# 3. Approved Packages (`packages.yml`)

Standard set:
```yaml
packages:
  - package: dbt-labs/dbt_utils
    version: [">=1.1.0", "<2.0.0"]
  - package: calogica/dbt_expectations
    version: [">=0.10.0", "<0.11.0"]  # only if doing distribution / advanced tests
  - package: dbt-labs/codegen
    version: [">=0.12.0", "<0.13.0"]  # dev convenience: scaffold staging models
```

Rules:
- New packages require an ADR
- Pin to compatible major versions (`>=X.Y, <X+1`)
- `dbt-expectations` is optional; teams without distribution-test discipline
  should keep schema tests (unique, not_null, accepted_values, relationships)
  as the floor

---

# 4. Materialization Defaults

Per layer:

| Layer | Default materialization | Why |
|---|---|---|
| `staging/` | `view` | Cheap, always-fresh; pushdown to warehouse |
| `intermediate/` | `ephemeral` or `view` | Composable; avoid storage churn |
| `marts/` | `table` (small) or `incremental` (large) | Query performance matters here |
| `snapshots/` | `snapshot` | SCD2 by definition |

Override in `dbt_project.yml`:
```yaml
models:
  my_project:
    staging:
      +materialized: view
    intermediate:
      +materialized: ephemeral
    marts:
      +materialized: table
```

Incremental models require an explicit unique key and a clearly documented
`is_incremental()` branch. New incremental models require an ADR.

---

# 5. Linting + Formatting

- **SQLfluff** (`>=3.0`) with the dbt templater — one source of truth for SQL style
- `.sqlfluff` at repo root pins dialect + rules
- Pre-commit hook: `sqlfluff lint` (blocking) + `sqlfluff fix --force` (warn)
- No tabs; 4-space indent; lowercase keywords; trailing commas in CTE lists

---

# 6. Environment + Targets

`profiles.yml` defines targets:
- `dev` — developer-personal schema (e.g. `analytics_dev_jane`)
- `ci` — ephemeral schema per PR (slim CI)
- `staging` — pre-prod, scheduled refresh
- `prod` — production, scheduled refresh + alerting

Rules:
- Credentials live in environment variables / secrets manager, NEVER in
  `profiles.yml` committed to git
- `dev` and `ci` MUST mask PII (per `PII_HANDLING.md`); `prod` is the only
  environment where un-masked PII is allowed
- See `docs/data/architecture/ENVIRONMENTS.md` for the cross-environment contract

---

# 7. CI Gates

Minimum gates that block merge (per `docs/data/architecture/DATA_QUALITY_CONTRACT.md`):

1. `sqlfluff lint` — style + parseability
2. `dbt parse` — manifest builds
3. `dbt build --select state:modified+` — only changed models + their downstream
4. `dbt test --select state:modified+` — schema tests pass with severity `error`
5. PII-column tag presence (custom script) when columns appear in marts touching `customer.*`

`dbt-expectations` tests, if used, MUST run in CI and MAY block merge depending
on severity (see `TESTING.md`).

---

# 8. When an ADR Is Required

- Adding a new dbt package
- Adding a new warehouse adapter
- Adopting a new materialization pattern (e.g. snapshots, incremental)
- Introducing a new layer between staging / intermediate / marts
- Bypassing the staging layer for a source
- Exposing a mart to a new downstream system (e.g. reverse-ETL, BI tool)

ADR template: `docs/data/architecture/ADR/TEMPLATE.md`
