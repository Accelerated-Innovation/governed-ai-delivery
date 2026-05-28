# PII Handling Contract

This document defines what counts as PII in this repository, how it's
classified, and the cross-environment rules for masking + access. The
stack-specific HOW (macros, scripts, CI gates) lives in the overlay's
`PII_HANDLING.md`.

---

# 1. PII Categories

| Category | Examples | Masking in non-prod |
|---|---|---|
| `identity` | Full name, home address, date of birth | Hashed or replaced with synthetic equivalent |
| `contact` | Email, phone number | Hashed (`pii.` + md5) |
| `sensitive` | SSN, government IDs, financial account numbers | Replaced with literal `REDACTED` |
| `device` | IP address, device fingerprint, full user agent | Truncated (last octet of IP; coarse UA) |

Adding a new category requires an ADR.

---

# 2. Tagging Discipline

Every column in `staging/` carrying PII must be tagged in its `_<model>.yml`:

```yaml
columns:
  - name: customer_email
    meta:
      contains_pii: true
      pii_category: contact
```

Tags propagate down the lineage automatically (in the lineage tool) but
must be re-declared at the mart level (defensive: an analyst reading
mart metadata in isolation should see the tag without checking upstream).

---

# 3. Per-Environment Behavior

| Environment | PII visible? | Who can query? |
|---|---|---|
| `dev` (developer-personal schema) | NO — always masked | The developer + their team |
| `ci` (PR-ephemeral schema) | NO — always masked | CI service + PR reviewer |
| `staging` | Yes IF analyst has the un-mask role; else masked | Restricted to analysts with the role |
| `prod` | Yes IF user has the warehouse RBAC role | Restricted role; audited access |

The masking mechanism is stack-specific (see overlay's `PII_HANDLING.md`).
The contract above applies regardless.

---

# 4. Right-to-Be-Forgotten

When a deletion request arrives:

1. Source system performs the deletion (we don't delete from sources; we
   transform sources)
2. Next staging refresh propagates the deletion (NULL or absence)
3. Marts rebuild without the customer (for SCD1) OR retain history with
   PII fields masked (for SCD2 snapshots)
4. Lineage tool's PII view confirms no residual rows

Document the deletion in an audit log. Quarterly audit verifies the path
still works end-to-end (use a synthetic customer as a canary).

---

# 5. Logging + Telemetry

PII must NOT appear in:
- dbt logs (`{{ log() }}`, `dbt run --debug` output)
- Pipeline orchestrator logs (Airflow task logs, Dagster event logs)
- Application traces / spans
- Slack / PagerDuty alerts
- Test failure messages

Use opaque IDs (`customer_id`) when referencing rows in logs. If a
debug session genuinely needs PII context, do it in a un-masked-env
ad-hoc query, not via logs.

---

# 6. Fixtures + Seeds

- `seeds/` (committed reference data): NO PII, ever. Use synthetic data.
- Test fixtures (in `tests/` or analogous): synthetic only. Generators that
  produce realistic-looking but fake PII are fine.
- Dev databases pre-populated from prod snapshots: must go through the
  masking macro before being made available; document the snapshot date
  in the dev environment's README.

---

# 7. When PII Is Allowed in a Mart

A mart that exposes individual-level PII must:
- Be tagged (every PII column flagged in `_<model>.yml`)
- Be access-controlled at the warehouse RBAC level
- Have an exposure entry naming the consumer and the business case
- Be reviewed quarterly (calibration session) to confirm the case still applies

Marts that don't meet these are aggregate-only — drop the PII columns and
re-issue.

---

# 8. Anti-Patterns

- "Just this once" un-masked debug query in `staging` env (never one-time;
  always one of many)
- PII in a model name or column comment (defeats tagging)
- A masking macro that's optional ("we'll add it later") — make it
  mandatory in CI, ship without it never
- Storing PII in seeds because "the source went away" (use synthetic; if
  the source is gone, the data is too)
