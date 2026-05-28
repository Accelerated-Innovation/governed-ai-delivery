# Design Principles — Data

These principles guide how the team and AI agents design data pipelines
+ models in this repository.

---

# 1. Declarative over imperative

Codify WHAT the data should look like (schema tests, distribution checks,
freshness SLAs) rather than HOW the pipeline produces it. SQL transforms
in dbt models > Python scripts manipulating data frames. When imperative
code is unavoidable (custom singular tests, macros, orchestration), keep
it small + testable in isolation.

---

# 2. Idempotency by default

Every model produces the same output for the same inputs, regardless of
when it's run. Backfills and partial reruns don't double-count, drop, or
corrupt data. Incremental models declare their unique key and have a
clearly bounded `is_incremental()` branch.

---

# 3. Source-of-truth thinking

Source systems own the truth of their data. The data project transforms +
serves; it does not BECOME the truth. Right-to-be-forgotten flows from
the source; cohort definitions live with the source owner; reference
data has a clear single-source-of-truth designation.

---

# 4. Test the contract, not the data

Distribution tests are useful but inherently calibration-sensitive. Schema
tests (unique, not_null, accepted_values, relationships) are the floor —
they encode the contract. Distribution / quality tests are the next tier
and should be promoted from `warn` to `error` only after the threshold
has held stable.

---

# 5. Lineage is documentation

A model without declared upstream sources + downstream consumers is
undocumented, regardless of its description. Exposures and source files
are part of the model's contract, not optional metadata.

---

# 6. Environments are firewalls

`dev`, `ci`, `staging`, `prod` are not just naming conventions — they're
data isolation boundaries. PII masking, access control, refresh cadence,
and alerting all differ per environment per `ENVIRONMENTS.md`.

---

# 7. Marts are the public API

Downstream consumers (BI, services, reverse-ETL) read marts. Therefore
mart schemas evolve like an API: additive changes are safe; removals and
renames are breaking changes that require deprecation periods and
consumer coordination.

---

# 8. Cost matters

Compute and storage are not free. The team tracks:
- Cost per model per run (warehouse credits)
- Storage per dataset (and prunes unused intermediate tables)
- Query cost on the BI side (slow marts get optimization attention)

Cost is a first-class quality dimension alongside correctness + freshness.

---

# 9. Agents follow the contracts, not their training data

An AI agent generating a new model in this repo:
- Reads the layer's `BOUNDARIES.md` before placing the model
- Cites the contract files it's relying on
- Doesn't introduce new packages, materializations, or layers without an ADR
- Doesn't generate PII-containing fixtures or seeds
- Asks before crossing a boundary
