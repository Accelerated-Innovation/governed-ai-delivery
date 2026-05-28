# Governed AI Delivery — Foundations (Level 3) — Codex (Data)

These instructions are mandatory. Codex operates as a governed delivery system
aligned to your data architecture contracts.

Repository artifacts are the source of truth. Chat history is not.

> **Feature artifacts are not part of L3.** If your team adopts spec-driven
> feature delivery (per-feature `acceptance.feature`, `nfrs.md`, `plan.md`,
> `eval_criteria.yaml`, and `architecture_preflight.md`), upgrade with
> `govkit apply --level 4`.

---

## Operating Mode

Codex operates aligned to:

- Architecture contracts under `docs/data/architecture/`
- Layer-scoped rules via nested `AGENTS.md` files under `models/`

Before generating or modifying models, tests, macros, or seeds:

- Read the architecture contracts relevant to the layer you are touching
  (see Architecture Contracts below)
- Apply pipeline, quality, PII, lineage, and environment contracts as binding
  constraints
- Confirm boundary rules in `docs/data/architecture/BOUNDARIES.md`
  (staging → intermediate → marts directionality)

If required inputs are missing or unclear, stop and ask.

---

## Architecture Contracts

Your project's data architecture is documented in `docs/data/architecture/`.
Read the contract relevant to what you are touching:

| Concern                | Document                       | Content                                                          |
| ---------------------- | ------------------------------ | ---------------------------------------------------------------- |
| Architecture model     | `ARCH_CONTRACT.md`             | Top-level architecture, approved tooling                         |
| Layer boundaries       | `BOUNDARIES.md`                | staging → intermediate → marts directionality + read/write rules |
| Pipelines              | `PIPELINE_CONTRACT.md`         | What is a pipeline + required metadata + ownership               |
| Data quality           | `DATA_QUALITY_CONTRACT.md`     | Test tiers + severity + what blocks merge                        |
| PII                    | `PII_HANDLING_CONTRACT.md`     | PII categories + per-environment masking rules                   |
| Lineage                | `LINEAGE_CONTRACT.md`          | What must be captured + retained                                 |
| Environments           | `ENVIRONMENTS.md`              | dev / ci / staging / prod isolation                              |

Stack-specific guidance lives in the overlay docs at the same path
(`TECH_STACK.md`, `TESTING.md`, `MODEL_LAYERING.md`, `QUERY_CONVENTIONS.md`,
`PII_HANDLING.md`, `LINEAGE_OBSERVABILITY.md`).

Layer-specific rules load automatically via nested `AGENTS.md` files when
working in each layer:

- `models/staging/AGENTS.md` — source-shaped cleanup; one `source()` per model
- `models/intermediate/AGENTS.md` — business logic; cross-source joins
- `models/marts/AGENTS.md` — the public contract; exposures + breaking-change rules
- `.agents/rules/data-quality.md` — test floor + severity policy
- `.agents/rules/pii.md` — PII tagging + masking
- `.agents/rules/repo-scope.md` — when to touch this repo vs. another

---

## Always check `.govkit/skill_context.yaml`

The team's actual architecture style + layer-to-folder mapping lives there.
Read it before assuming the default layer names — the team may use medallion
(bronze / silver / gold) or a custom layout.
`skill_context.architecture.layers.inbound` / `domain` / `outbound` map to the
team's source-shaped / business-logic / serving folders respectively.

---

## Implementation Rules

- Respect all rules in `docs/data/architecture/BOUNDARIES.md`
- Staging reads exactly one `{{ source(...) }}`; never another `ref()`, never a
  raw warehouse table
- Business logic lives in `intermediate/`, never in staging or marts
- Marts read from `intermediate/` (or other marts) only and are a public
  contract — treat the column list as an API
- Use only approved tooling and materializations from
  `docs/data/architecture/TECH_STACK.md`
- Apply masking via the project's `mask_pii()` macro per
  `docs/data/architecture/PII_HANDLING.md`; masking is unconditional in dev + ci
- Test-first is recommended for new models; the binding test-first rule is part
  of the Level 4 Spec-Driven Add-On

---

## ADR Rules

An Architecture Decision Record (ADR) is required when:

- A layer boundary is crossed (mart reading staging directly, intermediate
  reading marts)
- The staging layer is bypassed for a new source
- A test is skipped (severity downgrade, `--exclude` in CI)
- A new dbt package, materialization, or layer is introduced
- A mart is exposed to a new downstream system
- A mart column is removed, renamed, or has its semantics changed

ADRs live under `docs/data/architecture/ADR/`, follow
`docs/data/architecture/ADR/TEMPLATE.md`, and must be Accepted before
implementation proceeds. Invoke `$adr-author` to scaffold a new ADR.

---

## Testing Requirements

Each change must include, per `docs/data/architecture/DATA_QUALITY_CONTRACT.md`:

- Primary key `unique` + `not_null` tests (severity `error`)
- A description for every column declared in `_<model>.yml`
- `relationships` tests on FK columns pointing at the parent dimension
- Custom singular tests for invariants that don't fit a column-level test

---

## PII Discipline

- Tag every PII column in `_<model>.yml` with `meta.contains_pii: true` and a
  `pii_category`
- Never commit real PII in `seeds/`, `tests/`, or `macros/`; use clearly-fake
  synthetic values (`555-0100`, `example.com`)
- PII must not appear in dbt logs, orchestrator logs, alerts, or test failure
  messages — use opaque IDs

---

## Output Expectations

Every implementation output must include:

- Referenced architecture contracts
- ADR status (Accepted / pending / not required — with justification)
- Boundary + PII compliance confirmation
- Test coverage summary

If alignment is unclear, stop and ask.

---

## Authority

Architecture decisions belong to the Architect. Exceptions require an ADR and
explicit approval. Codex follows standards — it does not invent them.

---

## Upgrading to Spec-Driven Add-On (Level 4)

When your team is ready to adopt per-feature spec contracts, upgrade with:

```
govkit apply --level 4 --target <path>
```

Level 4 layers the following on top of Level 3:

- `features/<name>/` directory model with the 5-artifact governed contract
- `$architecture-preflight`, `$spec-planning`, `$implementation-plan` skills
- Test-first and spec-compliance rules (binding, not just recommended)
- Evaluation prediction discipline (FIRST + 7 Virtues, average ≥ 4.0)
- Governance CI jobs: artifact existence, eval-criteria schema, prediction
  thresholds
