# Testing Standards — dbt

This document defines the testing policy for this data repository.

The dbt test model is **declarative**: tests live alongside model definitions
in `_<model>.yml` files. CI runs `dbt test` against changed models + their
downstream lineage.

---

# 1. Test Tiers

| Tier | Tool | Severity | Blocks deploy? |
|---|---|---|---|
| **Schema tests** (`unique`, `not_null`, `accepted_values`, `relationships`) | dbt-core | `error` | YES |
| **Distribution tests** (row count thresholds, expected value ranges) | dbt-expectations | `warn` by default; `error` for critical models | Only on `error` |
| **Custom singular tests** (`tests/*.sql`) | dbt-core | `error` | YES |
| **Source freshness** (`dbt source freshness`) | dbt-core | `warn` | NO (alert only) |

A model fails CI when any `error`-severity test fails on the model OR its
downstream lineage (`dbt build --select state:modified+`).

---

# 2. Required Tests Per Model

Every model must have, in its `_<model>.yml`:

```yaml
models:
  - name: dim_customers
    columns:
      - name: customer_id
        tests: [unique, not_null]
      - name: customer_email
        tests: [not_null]
```

Minimum bar:
- Primary key: `unique` + `not_null`
- Every column declared (description present); untested non-PK columns are OK
  but flagged in code review

---

# 3. Custom Singular Tests

For invariants that don't fit a column-level test, write a `tests/*.sql` that
returns rows ONLY when the invariant is violated:

```sql
-- tests/dim_customers_email_lowercase.sql
select customer_id, customer_email
from {{ ref('dim_customers') }}
where customer_email != lower(customer_email)
```

Rules:
- File name describes the invariant (`assert_<model>_<property>.sql` or just `<model>_<rule>.sql`)
- The query returns the offending rows — empty result = test passes
- Severity defaults to `error`; override in `.yml` if needed

---

# 4. dbt-expectations (Optional, L4+)

For teams adopting distribution / quality discipline:

```yaml
models:
  - name: fct_orders
    tests:
      - dbt_expectations.expect_table_row_count_to_be_between:
          min_value: 1000
          max_value: 1000000
          severity: warn
      - dbt_expectations.expect_column_quantile_values_to_be_between:
          column: order_total_usd
          quantile: 0.99
          min_value: 100
          max_value: 50000
          severity: warn
```

Rules:
- Distribution tests start as `warn` — promote to `error` only after the
  threshold has held stable for ≥ 2 weeks
- Document the WHY in `description:` ("expected range based on Q1 2026
  historical data; review quarterly")

---

# 5. Source Freshness

Declare in `_sources.yml`:

```yaml
sources:
  - name: stripe
    tables:
      - name: customers
        loaded_at_field: updated_at
        freshness:
          warn_after: {count: 12, period: hour}
          error_after: {count: 24, period: hour}
```

Rules:
- Every source table that feeds a daily mart has a `freshness:` block
- Warn / error thresholds chosen against the source's known cadence
- Freshness failures alert oncall; they don't block deploy (the source is
  not the merge requester's fault)

---

# 6. CI Test Selection

Standard `slim CI` pattern:

```bash
# In CI on a PR
dbt deps
dbt parse
dbt build --select state:modified+ --defer --state ./prod-artifacts
dbt test --select state:modified+ --defer --state ./prod-artifacts
```

`--defer` + `--state ./prod-artifacts` means changed models are built in a
PR-scoped schema, and unchanged dependencies are read from production. CI
time stays bounded; correctness preserved.

---

# 7. When BDD-Style Tests Apply (L4)

`docs/<feature>/acceptance.feature` Gherkin scenarios cover end-to-end
data contracts that span multiple models or multiple runs:

```gherkin
Feature: Customer dimension daily refresh

  @nfr-freshness
  Scenario: Most recent load no older than 1 hour after the daily run
    Given the customer_dim_daily job ran at 06:00 UTC
    Then by 07:00 UTC the most_recent_load_at SHALL be ≤ 1 hour stale
```

These are validated by a separate CI step that queries the warehouse after
the job runs — not by dbt itself. See `features/starter_data/` for the
worked example.

---

# 8. What NOT to Test

- Source data quality (that's the upstream owner's responsibility — flag via
  `source freshness` + alerting, don't gate your CI on it)
- Warehouse infrastructure (compute, network — different test surface)
- Visual dashboards (different tool stack — BI tests live with the dashboard)
