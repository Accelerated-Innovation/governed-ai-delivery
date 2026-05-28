# Model Layering — staging / intermediate / marts

This document defines the dbt model layering convention for this repository.
AI agents creating new models must place them in the correct layer.

The default convention is **staging / intermediate / marts**. Teams using
medallion (bronze / silver / gold) can swap the layer names by editing this
file and the `skill_context.architecture.layers` block — the contracts below
still apply.

---

# 1. Layer Definitions

## staging/ — source-shaped

**Purpose:** present source data with light cleaning, ready for joins downstream.

What goes here:
- Column renames (`id` → `customer_id`)
- Type casts (`text` → `timestamp`)
- Light value cleanup (`lower(email)`, `trim(name)`)
- Filter out clearly invalid rows (NULL primary key)

What does NOT go here:
- Joins across sources
- Business logic / aggregations
- Calculated fields beyond trivial reshaping

Materialization: `view` (default)

## intermediate/ — business transformations

**Purpose:** compose staging models into reusable business entities.

What goes here:
- Joins across staging models from the same source OR across sources
- Window functions (running totals, ranking)
- Aggregations producing reusable building blocks
- Pre-computed segments / categorizations

What does NOT go here:
- Final serving shapes (those go in marts)
- One-off calculations used by exactly one mart (inline it instead)

Materialization: `ephemeral` (default) or `view`

## marts/ — serving layer

**Purpose:** the contract consumed by BI tools, applications, and humans.

What goes here:
- Dimensional tables (`dim_*`)
- Fact tables (`fct_*`)
- Pre-aggregated rollups for dashboards
- Domain-shaped denormalized tables (`customer_360`)

What does NOT go here:
- Source-shaped data (push to staging)
- Reusable building blocks (push to intermediate)

Materialization: `table` (small) or `incremental` (large)

---

# 2. Boundary Rules

These are enforced by code review (and, optionally, by `dbt-project-evaluator`):

| From | Allowed `ref()` targets |
|---|---|
| `staging/` | sources only (no other models) |
| `intermediate/` | staging + other intermediate |
| `marts/` | intermediate + other marts |

**Forbidden:**
- marts → staging (bypasses business logic)
- intermediate → marts (downstream reference)
- any model → raw warehouse tables (must go through a source)

Violations require an ADR documenting why and what alternative was considered.

---

# 3. Cross-Source Models

When a model joins data from multiple sources:
- Live in `intermediate/` (never staging)
- Naming: `int_<domain>__<verb>.sql` (e.g. `int_customers__joined_to_orders.sql`)
- Document the join key + cardinality in the model description
- Test the join: `dbt_utils.relationships` confirms FK validity

---

# 4. Marts Are the Contract

Downstream systems (BI, services, reverse-ETL) read from `marts/` only. Therefore:

- Schema changes in `marts/` are breaking changes; treat the column list as
  a public API
- New mart columns are additive — safe to ship
- Removing or renaming mart columns requires:
  1. Deprecation notice in `description:` for one release cycle
  2. Coordination with downstream consumers (BI dashboard owners, app teams)
  3. ADR documenting the migration plan

Document mart consumers in `models/marts/_exposures.yml`:

```yaml
exposures:
  - name: customer_360_dashboard
    type: dashboard
    url: https://looker.example.com/dashboards/42
    depends_on:
      - ref('dim_customers')
      - ref('fct_orders')
    owner:
      name: Analytics Team
      email: analytics@example.com
```

`dbt docs` then surfaces "what breaks if I change this mart" automatically.

---

# 5. Snapshots (SCD2)

Slowly-changing dimension tracking lives in `snapshots/`, separate from the
three main layers. Snapshots read from sources (not from staging) so that
the captured timestamps reflect when the source actually changed, not when
the dbt model ran.

Required snapshot config:
- `strategy: timestamp` (preferred) or `strategy: check` with explicit
  `check_cols`
- `unique_key:` on the natural key
- `updated_at:` on the source's actual update timestamp

---

# 6. Anti-Patterns

- A "staging" model that aggregates (move to intermediate)
- An intermediate model that's referenced by exactly one mart (inline it)
- A mart that's never queried (delete it)
- Two marts with overlapping concepts (consolidate)
- A snapshot that reads from staging instead of source (defeats the purpose)
