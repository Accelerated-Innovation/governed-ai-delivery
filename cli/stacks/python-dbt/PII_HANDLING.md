# PII Handling — dbt Implementation

This document defines how dbt models in this repository handle PII
(personally identifiable information). The universal contract lives at
`docs/data/architecture/PII_HANDLING_CONTRACT.md`; this file is the
dbt-specific HOW.

---

# 1. PII Classification

Columns are tagged in `_<model>.yml` with `meta`:

```yaml
models:
  - name: stg_stripe__customers
    columns:
      - name: customer_email
        description: Email, lowercased
        meta:
          contains_pii: true
          pii_category: contact
      - name: customer_phone
        meta:
          contains_pii: true
          pii_category: contact
      - name: customer_ssn_last4
        meta:
          contains_pii: true
          pii_category: sensitive  # stricter masking
```

Categories used in this repo:
- `identity` — name, email, phone, address
- `contact` — email, phone
- `sensitive` — SSN, DOB, government IDs, financial account numbers
- `device` — IP, device ID, user agent

Adding a new category requires an ADR.

---

# 2. Per-Environment Masking

A custom macro `mask_pii(column, category)` applies env-conditional masking:

```sql
-- macros/mask_pii.sql
{% macro mask_pii(column_name, category='contact') %}
    {% if target.name in ('dev', 'ci') %}
        {% if category == 'sensitive' %}
            'REDACTED'
        {% else %}
            'pii.' || md5({{ column_name }})
        {% endif %}
    {% else %}
        {{ column_name }}
    {% endif %}
{% endmacro %}
```

Usage in staging:

```sql
select
    id                                      as customer_id,
    {{ mask_pii('email', 'contact') }}      as customer_email,
    {{ mask_pii('phone', 'contact') }}      as customer_phone,
    {{ mask_pii('ssn_last4', 'sensitive') }} as customer_ssn_last4
from {{ source('stripe', 'customers') }}
```

Rules:
- `dev` and `ci` MUST mask PII (per `docs/data/architecture/ENVIRONMENTS.md`)
- `staging` (the env, not the layer) may un-mask if and only if the analyst
  has been granted access via the warehouse RBAC role
- `prod` un-masks; access controlled by warehouse role

---

# 3. CI Gate: PII Tag Coverage

A custom script (`scripts/check_pii_tags.py` — author per project) parses
`models/staging/*/_<model>.yml` and confirms:
- Every column matching `email`, `phone`, `ssn`, `dob`, `address`, `name`
  has `meta.contains_pii: true`
- Every column flagged `contains_pii` is wrapped in `mask_pii()` in the
  staging model SQL

The gate runs in CI; failure blocks merge.

---

# 4. PII in Marts

Marts MUST inherit the PII tags from their upstream models (re-declare in
the mart's `_<model>.yml`). The macro re-applies masking at the mart layer.

Aggregated marts that don't carry individual-level PII don't need the tag
(e.g. `fct_monthly_revenue` is aggregate-only). Document with:

```yaml
models:
  - name: fct_monthly_revenue
    description: |
      Monthly revenue aggregated across all customers. NO individual-level
      PII; safe to expose to broader analyst access.
```

---

# 5. Right-to-Be-Forgotten (GDPR)

When a customer requests deletion:

1. Source system tombstones / hard-deletes the record
2. `staging/` picks up the change on next refresh (NULL or absence)
3. Marts re-build with the customer absent (full refresh for SCD1; SCD2
   snapshots retain history but mask the affected fields)

The dbt project should NOT independently delete records — defer to source
of truth. Audit the deletion path quarterly per the universal contract.

---

# 6. Snapshots + PII

PII in snapshots is tricky: SCD2 history captures values at every change.
Rules:
- Snapshot tables tagged `contains_snapshot_pii: true` in `meta` at the
  table level
- Apply `mask_pii()` in the snapshot SELECT clause when env != prod
- Retention policy declared in snapshot config (`+post-hook` runs
  `delete from {{ this }} where dbt_valid_to < ...`)

---

# 7. Anti-Patterns

- Selecting PII columns in marts without masking (CI gate catches this)
- Hardcoded test data containing real PII (use synthetic data only)
- PII in `seeds/` (forbidden — seeds are committed)
- Logging PII via dbt's `{{ log() }}` macro (forbidden; use opaque IDs)
- PII in model column names (e.g. `email_AT_gmail`) — defeats masking
