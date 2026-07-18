# Governed AI Delivery — Data Project Governance

This repository ships data pipelines + models. Claude must follow the
contracts in `docs/data/architecture/` when writing or modifying anything
in this repo.

---

## Always read these before writing code

- `docs/data/architecture/ARCH_CONTRACT.md` — top-level architecture
- `docs/data/architecture/BOUNDARIES.md` — layer boundary rules (staging →
  intermediate → marts directionality)
- `docs/data/architecture/PIPELINE_CONTRACT.md` — what's a pipeline + required
  metadata
- `docs/data/architecture/DATA_QUALITY_CONTRACT.md` — test tiers + severity +
  what blocks merge
- `docs/data/architecture/PII_HANDLING_CONTRACT.md` — PII categories +
  per-environment masking rules
- `docs/data/architecture/LINEAGE_CONTRACT.md` — what must be captured +
  retained
- `docs/data/architecture/ENVIRONMENTS.md` — dev / ci / staging / prod
  isolation

Stack-specific guidance lives in the overlay docs at the same path
(`TECH_STACK.md`, `TESTING.md`, `MODEL_LAYERING.md`, `QUERY_CONVENTIONS.md`,
`PII_HANDLING.md`, `LINEAGE_OBSERVABILITY.md`).

---

## Always check `.govkit/skill_context.yaml`

The team's actual architecture style + layer-to-folder mapping lives there.
Read it before assuming the default layer names — the team may use medallion
(bronze / silver / gold) or a custom layout.

`skill_context.architecture.layers.inbound` / `outbound` / `domain` map to
the team's source-shaped / serving / business-logic folders respectively.

---

## Layer-scoped rules (loaded automatically)

- `.claude/rules/govkit/staging.md` — staging-model conventions
- `.claude/rules/govkit/intermediate.md` — intermediate-model conventions
- `.claude/rules/govkit/marts.md` — mart conventions (the public contract)
- `.claude/rules/govkit/data-quality.md` — testing discipline + severity policy
- `.claude/rules/govkit/pii.md` — PII tagging + masking
- `.claude/rules/govkit/repo-scope.md` — when to touch this repo vs. another

Rule globs in this install are templated to your actual folder layout at
install time (see `paths:` in each rule's frontmatter). If the globs don't
match files in your repo, run `govkit doctor --target .` for specific
mismatches.

---

## When you're stuck

- Cite the contract you're following ("per `BOUNDARIES.md` §3, marts may not
  read from staging directly...")
- If a contract is ambiguous, draft an ADR proposal rather than picking one
  interpretation silently
- For PII concerns, **always** check `PII_HANDLING_CONTRACT.md` before
  generating fixtures, seeds, or test data

---

## What NOT to do without an ADR

- Cross a layer boundary (mart reading staging directly, intermediate
  reading marts)
- Bypass the staging layer for a new source
- Skip a test (severity downgrade, `--exclude` in CI)
- Introduce a new dbt package, materialization, or layer
- Expose a mart to a new downstream system
- Generate test data containing real-looking PII
- Reference raw warehouse tables (always go through a `source()`)
