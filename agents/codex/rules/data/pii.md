# PII Handling

**Authority:**
- `docs/data/architecture/PII_HANDLING_CONTRACT.md` — categories + per-env rules
- `docs/data/architecture/PII_HANDLING.md` (stack overlay) — stack-specific HOW

This rule fires when editing any model, macro, seed, or test.

## Categories

| Category | Examples | Non-prod treatment |
|---|---|---|
| `identity` | Name, address, DOB | Hashed or synthetic |
| `contact` | Email, phone | Hashed |
| `sensitive` | SSN, gov't IDs, financial accounts | `REDACTED` literal |
| `device` | IP, device fingerprint | Truncated |

## Tagging

Every column carrying PII at the staging boundary tagged in `_<model>.yml`:
```yaml
columns:
  - name: customer_email
    meta:
      contains_pii: true
      pii_category: contact
```

Tags propagate down the lineage automatically but MUST be re-declared at
the mart level (defensive — an analyst reading mart metadata in isolation
should see the tag without checking upstream).

## Masking

Use the project's `mask_pii(column, category)` macro per the stack overlay's
`PII_HANDLING.md`. Masking is unconditional in `dev` + `ci` per
`ENVIRONMENTS.md` — no flag, no override.

## Forbidden in seeds + fixtures

- Real PII in any committed file: `seeds/`, `tests/`, `macros/` literal values
- "Anonymized" prod data: still PII (re-identification risk)
- Generated test data with realistic SSNs / phone numbers / emails:
  use synthetic patterns that are clearly fake (`555-0100` phone numbers,
  `example.com` emails)

## Forbidden in logs + alerts

PII must NOT appear in:
- dbt logs (`{{ log() }}`, `dbt run --debug`)
- Orchestrator logs (Airflow task logs, Dagster events)
- Slack / PagerDuty alerts
- Test failure messages (use opaque IDs in custom test queries)

## When you encounter PII

1. Check whether the field is tagged in staging
2. If not tagged, tag it (don't proceed without the tag)
3. Apply masking via `mask_pii()` per the overlay's macro
4. Add a test case in `_<model>.yml` if the field is also a uniqueness key

## When in doubt

If a column COULD be PII but isn't obviously so (e.g., `display_name`,
`profile_url`), tag it. Over-tagging has near-zero cost; under-tagging
is a compliance incident.

## Anti-patterns

- "We'll add masking later" — no; ship with masking or don't ship
- A test that asserts a specific email value (use a pattern match instead)
- PII in a column NAME (`email_for_billing` is fine; `john_smith_email`
  is a leak)
- Logging the row that failed a test (log the opaque ID, not the row)
