# Governed AI Delivery — Data Project Governance (L4 — Spec-Driven Add-On)

This repository is at **Level 4 — Spec-Driven Add-On**. Every feature ships
with the L3 baseline contracts (see the L3 governance content above) PLUS a
spec-driven feature package.

---

## Mandatory Feature Structure (L4)

For every new feature in `features/<feature_name>/`:

1. **`acceptance.feature`** — Gherkin scenarios describing the end-to-end
   data contract (freshness, quality, lineage, PII)
2. **`nfrs.md`** — non-functional requirements (freshness SLA, masking,
   reliability, observability)
3. **`eval_criteria.yaml`** — the success criteria CI checks against
4. **`architecture_preflight.md`** — produced by the
   `/architecture-preflight` skill before any code lands
5. **`plan.md`** — produced by `/implementation-plan` after preflight; lists
   the dbt models / orchestrator changes / tests required, ordered

Implementation must not begin unless all five artifacts exist for the
feature.

---

## Gherkin for Data

Data scenarios use the same Given / When / Then structure as backend, but
the vocabulary is different. See `features/starter_data/` for the worked
example. Common shapes:

```gherkin
@nfr-freshness
Scenario: Most recent load no older than 1 hour after daily run
  Given the <pipeline> ran at <expected_start_time>
  Then by <expected_completion_time> the most_recent_load_at metric
       SHALL be ≤ <freshness_threshold> stale

@nfr-quality
Scenario: Uniqueness invariant on natural key
  Given a successful refresh of <mart>
  Then <natural_key> SHALL be unique
  And <natural_key> SHALL be non-null for every row

@nfr-pii
Scenario: PII masked outside production
  Given an analyst querying <mart> in the <env> environment
  Then PII columns SHALL be masked per PII_HANDLING_CONTRACT.md
```

NFR tags map to the categories in `nfrs.md`. The eval gate checks that
every NFR category has at least one tagged scenario.

---

## Skills Available

- `/architecture-preflight <feature>` — analyzes inputs + produces
  `architecture_preflight.md`
- `/spec-planning <feature>` — drafts the Gherkin + NFRs scaffolding
- `/implementation-plan <feature>` — produces the ordered `plan.md`
- `/adr-author` — drafts an ADR when a contract violation is required

These skills read `.govkit/skill_context.yaml` for the team's actual
architecture style — they do NOT assume hexagonal / clean / layered /
medallion / dbt staging-intermediate-marts. Whatever your layer
mapping is, the skills follow it.

---

## Validation

Run `govkit validate` to check that all five artifacts are present and
internally consistent for every feature. Run `govkit doctor` to check
that the installed governance still matches your repo (rule globs,
detected stack, CI gates).
