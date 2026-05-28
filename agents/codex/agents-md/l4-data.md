# Governed AI Delivery — Codex Agent Instructions (Data, Level 4)

These instructions are mandatory. Codex operates as a governed delivery system,
not an open coding environment. This is the **Level 4 — Spec-Driven Add-On** for
data projects: every feature ships the L3 baseline data contracts
(`docs/data/architecture/`, layer-scoped `AGENTS.md` rules) PLUS a spec-driven
feature package.

Repository artifacts are the source of truth. Chat history is not.

---

## Operating Mode

Codex operates aligned to:

- Product specifications under `features/`
- Architecture contracts under `docs/data/architecture/`
- Layer-scoped rules via nested `AGENTS.md` files under `models/`

Before planning or generating models, tests, or macros:

- Read the architecture contracts relevant to the layer you are touching
- Confirm boundary rules in `docs/data/architecture/BOUNDARIES.md`
  (staging → intermediate → marts)
- Confirm required feature artifacts exist

If required inputs are missing, stop and ask.

---

## Mandatory Feature Structure

Every feature must live under `features/<feature_name>/` with these required
artifacts:

- `acceptance.feature` — Gherkin scenarios describing the end-to-end data
  contract (freshness, quality, lineage, PII)
- `nfrs.md` — non-functional requirements (freshness SLA, masking, reliability,
  observability)
- `eval_criteria.yaml` — the success criteria CI checks against
- `architecture_preflight.md` — produced by `$architecture-preflight` before any
  model lands
- `plan.md` — produced by `$implementation-plan` after preflight; lists the dbt
  models / orchestrator changes / tests required, ordered

Implementation must not begin unless all five artifacts exist. If `nfrs.md`
contains TBD entries, or `acceptance.feature` has no scenarios, stop and request
completion.

---

## Gherkin for Data

Data scenarios use the same Given / When / Then structure as backend, but the
vocabulary differs. See `features/starter_data/` for the worked example. Common
shapes:

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

Every populated NFR category in `nfrs.md` must have at least one scenario tagged
with the corresponding `@nfr-*` tag. Verify coverage during Architecture
Preflight and plan finalization — stop if incomplete.

---

## Feature Lifecycle (Mandatory Order — no steps may be skipped)

1. Architecture Preflight → invoke `$architecture-preflight`
2. ADR creation (if required by preflight — see L3 ADR triggers)
3. Plan finalization → invoke `$spec-planning`
4. Incremental implementation → guided by `$implementation-plan`
5. Automated tests (schema + custom singular tests per
   `docs/data/architecture/DATA_QUALITY_CONTRACT.md`)
6. Data-quality and PII gates

The layer rules (`models/staging/AGENTS.md`, `models/intermediate/AGENTS.md`,
`models/marts/AGENTS.md`) and the cross-cutting `.agents/rules/data-quality.md`
and `.agents/rules/pii.md` remain binding at L4.

---

## Skills Available

- `$architecture-preflight <feature>` — analyzes inputs + produces
  `architecture_preflight.md`
- `$spec-planning <feature>` — drafts the Gherkin + NFRs scaffolding
- `$implementation-plan <feature>` — produces the ordered `plan.md`
- `$adr-author` — drafts an ADR when a contract violation is required

These skills read `.govkit/skill_context.yaml` for the team's actual layer
mapping (staging/intermediate/marts vs medallion bronze/silver/gold) — they do
not assume a fixed layout.

---

## Validation

Run `govkit validate` to check that all five artifacts are present and
internally consistent for every feature. Run `govkit doctor` to check that the
installed governance still matches your repo (detected stack, CI gates).

---

## Authority

Architecture decisions belong to the Architect. Exceptions require an ADR and
explicit approval. Codex follows standards — it does not invent them.
