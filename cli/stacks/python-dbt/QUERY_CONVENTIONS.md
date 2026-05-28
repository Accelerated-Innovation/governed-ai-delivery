# SQL + Jinja Conventions

This document defines query-writing conventions for dbt models in this
repository. AI agents writing new models must follow these patterns.

---

# 1. Model File Naming

Per layer:

| Layer | Naming | Example |
|---|---|---|
| `staging/` | `stg_<source>__<table>.sql` | `stg_stripe__customers.sql` |
| `intermediate/` | `int_<business_concept>__<verb>.sql` | `int_customers__joined_to_orders.sql` |
| `marts/` | `<concept>` (dim) / `<concept>` (fact) | `dim_customers.sql`, `fct_orders.sql` |

Rules:
- Staging model names mirror the source one-to-one
- Intermediate models describe the transformation, not the destination
- Marts use dimensional naming (`dim_*`, `fct_*`) or domain naming (`customer_360`)

---

# 2. CTE Style

Standard CTE skeleton for every model:

```sql
with

source as (
    select * from {{ source('stripe', 'customers') }}
),

renamed as (
    select
        id                  as customer_id,
        email               as customer_email,
        created             as created_at,
        updated             as updated_at
    from source
)

select * from renamed
```

Rules:
- One CTE per logical step; rename → filter → join → aggregate
- Final `select *` from the last CTE — never inline the final transformation
- CTE names are lowercase snake_case verbs or nouns (`renamed`, `joined`, `filtered`, `aggregated`)
- Avoid the `final` CTE anti-pattern; let the last named CTE describe what it produces

---

# 3. ref() and source()

- `staging/` models read from `{{ source(...) }}` — never directly from a warehouse table
- `intermediate/` and `marts/` read from `{{ ref(...) }}` — never raw, never source
- Sources are declared once per source system in `models/staging/<source>/_sources.yml`

Rule: a model that bypasses these conventions (raw schema reference, hardcoded
table name) must carry a `-- bypass: <reason>` comment and link to an ADR.

---

# 4. Jinja in Models

Allowed:
- `{{ ref(...) }}`, `{{ source(...) }}`, `{{ config(...) }}`
- `{{ var(...) }}` for environment-conditional behavior
- `{% if is_incremental() %} ... {% endif %}` in incremental models
- Date macros (`{{ dbt.dateadd(...) }}`, `{{ date_spine(...) }}`)

Discouraged:
- Multi-line Jinja blocks doing business logic (move to an intermediate model)
- Loops generating column lists from variables (use dbt-codegen at dev time, paste the result)
- Conditional column lists based on target (creates lineage drift)

---

# 5. Column Naming + Types

- Primary key on every model: `<concept>_id`, always non-null + unique
- Timestamps in UTC, suffix `_at` (`created_at`, `updated_at`, `loaded_at`)
- Booleans prefix `is_` or `has_` (`is_active`, `has_subscription`)
- Surrogate keys: `dbt_utils.generate_surrogate_key([...])` — document the input columns
- Type cast in staging only; downstream models trust types

---

# 6. Required Model Documentation

Every model has a `_<model>.yml` (or grouped `_<layer>.yml`) entry:

```yaml
version: 2

models:
  - name: dim_customers
    description: |
      One row per customer. Daily refresh. Owned by analytics-eng.
    columns:
      - name: customer_id
        description: Primary key
        tests: [unique, not_null]
      - name: customer_email
        description: Email, lowercased
        tests: [not_null]
```

Rules:
- A model without `description` fails CI
- Primary key column tested `unique` + `not_null`
- Columns containing PII tagged (`meta.contains_pii: true`) — see `PII_HANDLING.md`

---

# 7. Anti-Patterns

- `select *` in marts (breaks downstream consumers on schema changes)
- Cross-joins without an explicit `cross join` keyword
- Window functions without a partition (silently scans the whole table)
- Hardcoded date filters (use `{{ var('start_date') }}` or `current_date()`)
- "SELECT into" patterns (use `materialized: table` and let dbt manage)
- Untagged PII columns in marts (CI gate blocks this)
