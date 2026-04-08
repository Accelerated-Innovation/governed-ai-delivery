# Governed AI Delivery — Improvement Plan

> Generated 2026-04-02 from a comprehensive expert review of the entire project.
> This plan is the single source of truth for tracking improvement work.
> Each increment is designed to be atomic and independently committable.

---

## Tier 5 — Maturity Model (v0.3.0)

### 5.1 Level 3 / Level 4 Split
- [x] Create L3 feature starters (3 artifacts: acceptance.feature, nfrs.md, plan.md)
- [x] Create L3 plan templates (no evaluation_prediction block)
- [x] Create L3 generic agent rules (test-first.md, spec-compliance.md)
- [x] Create L3 CLAUDE.md variants (no architecture contracts, no evaluation scoring)
- [x] Create L3 agent skills (simplified spec-planning, implementation-plan)
- [x] Create L3 Copilot equivalents (instructions, prompts)
- [x] Create L3 CI templates (basic quality gates only)
- [x] Add `level_3` sub-key override to manifests
- [x] Add `--level` flag to CLI (apply, init, validate)
- [x] Write `.govkit` marker file on apply
- [x] Level-aware validation (3 artifacts for L3, 5 for L4)
- [x] Update agent-manifest schema for `level_3` override
- [x] Update tests (70 tests, all passing)
- [x] Update README, CHANGELOG, CI README

### 5.2 Level 5 — Self-Adapting Systems
- [ ] Requirements TBD — to be planned once L5 specification is provided

---

## Tier 1 — Critical Gaps (block effective use)

### 1.1 FIRST & 7 Virtues Scoring Rubrics
- [x] Create `docs/backend/evaluation/FIRST_SCORING_RUBRIC.md` with 1-5 scale definitions per principle (Fast, Isolated, Repeatable, Self-Verifying, Timely)
- [x] Create `docs/backend/evaluation/VIRTUE_SCORING_RUBRIC.md` with 1-5 scale definitions per virtue (Working, Unique, Simple, Clear, Easy, Developed, Brief)
- [x] Create `docs/ui/evaluation/FIRST_SCORING_RUBRIC.md` (UI-adapted version)
- [x] Create `docs/ui/evaluation/VIRTUE_SCORING_RUBRIC.md` (UI-adapted version)
- [x] Cross-reference rubrics from `eval_criteria.md` (backend and UI)

### 1.2 UI TECH_STACK.md Files
- [x] ~~Create UI TECH_STACK.md files~~ — already existed (review agent error). Added scoring rubric cross-references to both.

### 1.3 CLI Error Handling & Robustness
- [x] Add source path validation in `copy_entry()` before copy
- [x] Add `encoding="utf-8"` to all `read_text()` calls
- [x] Add try/except for `json.loads()` in `load_manifest()` and `cmd_list()`
- [x] Add manifest structure validation (required keys: agent, variants)
- [x] ~~Fix `pyproject.toml` import-linter `root_package`~~ — config is a reference template for target projects, not for govkit itself. Added clarifying comment.

### 1.4 Starter Template Variants
- [x] ~~Create separate deterministic starter~~ — `starter_cli` already uses mode: deterministic. Added mode selection instructions instead.
- [x] Add instructions at top of each starter's `eval_criteria.yaml` explaining mode selection (backend, cli — ui already had them)
- [x] Update README to reference mode selection in starters

### 1.5 Prediction vs Actual CI Gap
- [x] Document the approach in `ci/README.md` (what's enforced now vs predicted vs stubbed vs agent-only)
- [x] ~~Add placeholder CI jobs~~ — stubs already exist with clear "Configure your..." guidance. CI README now documents how to close each gap.
- [ ] Design approach for post-implementation CI jobs that compare actual test/lint/accessibility results to plan.md predictions (deferred — requires team-specific tooling)

---

## Tier 2 — Significant Gaps (incomplete governance)

### 2.1 Agent/CI Enforcement Alignment
- [x] Add CI job: check `features/*/architecture_preflight.md` exists for any feature with a plan.md (GitHub + Azure)
- [x] Add CI job: validate commit message format `feat|fix|docs|test(<scope>): ...` (GitHub + Azure)
- [x] Document which governance checks are agent-side vs CI-side (done in `ci/README.md` during Tier 1.5)

### 2.2 Evaluation Prediction Format Alignment
- [x] Standardize evaluation_prediction YAML schema (unified `first`/`virtues`/`accessibility` structure)
- [x] Align Copilot UI prompts to match the standardized format
- [x] Align Claude Code UI skills to match the standardized format
- [x] Add the schema to `governance/schemas/evaluation_prediction.schema.json`
- [x] Update UI eval-gate CI to parse standardized format with backward compatibility (GitHub + Azure)
- [x] Update worked example (`ui_task_dashboard/plan.md`) to use standardized format

### 2.3 Missing Architecture Artifacts
- [x] Create `docs/backend/architecture/OBSERVABILITY_PORT_CONTRACT.md` (port interface, adapter example, testing guidance)
- [x] Create `docs/backend/architecture/ERROR_MAPPING.md` (domain exception hierarchy, HTTP mapping, handler pattern)
- [x] Create `docs/backend/architecture/CROSS_CUTTING_CONCERNS.md` (DTOs, validation, pagination, timestamps, soft deletes, audit, config)
- [x] Add LangGraph vs LangChain decision matrix to `TECH_STACK.md` Section 4

### 2.4 Import-Linter Config
- [x] Create reference config at `governance/backend/importlinter-reference.toml` (with merge instructions)
- [x] ~~Add to manifests~~ — already distributed via `governance/backend/` shared artifact in both agents

### 2.5 Copilot Prompt Parity
- [x] Enhance `adr-author.prompt.md` — added template location and output path
- [x] Enhance `spec-planning.prompt.md` — added scoring rubric references
- [x] Enhance `implementation-plan.prompt.md` — added increment sizing guidance and rubric references
- [x] Enhance `architecture-preflight.prompt.md` — added output file path (backend + UI)

### 2.6 Backend vs UI Evaluation Harmonization
- [x] Add Virtue scoring check to UI eval-gate (done in 2.2 — both GitHub and Azure)
- [x] Aligned prediction format: both backend and UI now use `first`/`virtues`/`accessibility` structure
- [x] Remaining intentional difference: UI eval-gate additionally checks `accessibility.predicted_axe_violations == 0` (backend does not have accessibility checks). Documented in `ci/README.md`.

---

## Tier 3 — Documentation & DX

### 3.1 README Expansion
- [x] Add Prerequisites & System Requirements section
- [x] Add post-install verification section (what the target project should look like)
- [x] Add Concepts section before Quickstart (hexagonal architecture, FIRST, Gherkin, governance)
- [x] ~~Add concrete end-to-end walkthrough~~ — README now has detailed step-by-step + interactive prompt example + worked examples linked. Full standalone walkthrough deferred.
- [x] Add Troubleshooting & FAQ section (10 entries)
- [x] Add interactive prompt example output for `govkit apply`
- [x] Add Interpreting Validation Failures section (table of failures with fixes)

### 3.2 Terminology & Glossary
- [x] Add glossary to README (16 terms: agent, rule, skill, instruction, prompt, port, adapter, domain, FIRST, 7 Virtues, ADR, NFR, evaluation prediction, govkit validate, /architecture-preflight)
- [x] Clarified `/architecture-preflight` vs `govkit validate` distinction in glossary

### 3.3 Supporting Documents
- [x] Create `CONTRIBUTING.md` (project structure, common contributions, commit format, PR process, code style)
- [x] Create `CHANGELOG.md` (0.1.0 initial release + 0.2.0 with all improvements)
- [x] Add "Getting Help" section to README (issues link, contributing link, changelog link, CI reference)

### 3.4 Governance Structure Explanation
- [x] Add "Directory Roles" section to README explaining `docs/` vs `governance/` vs `features/` separation
- [x] Add new architecture docs and scoring rubrics to README reference links

---

## Tier 4 — Polish & Hardening

### 4.1 Schema & Validation Tightening
- [x] Add `eval_class` enum to `governance/backend/schemas/eval_criteria.schema.json` (retrieval_match, safety_classifier, structure_validator, tone_classifier, factual_accuracy, custom)
- [x] Create `governance/schemas/agent-manifest.schema.json` for manifest validation
- [x] Add Scenario Outline guidance to Gherkin conventions doc (when to use, tagging rules, examples)

### 4.2 CI Hardening
- [x] ~~Make bundle-size check blocking~~ — intentionally advisory since the tool requires project-specific configuration. Already documented with instructions to make blocking.
- [x] ~~Remove duplicate schema validation~~ — no actual duplication (backend quality-gate uses backend schema, UI quality-gate uses UI schema, eval-gate doesn't validate schemas). Review agent was incorrect.
- [x] Document SonarQube/Snyk as optional — updated both GitHub and Azure quality-gate headers to clarify these jobs should be removed if not used

### 4.3 CLI Polish
- [x] Add deduplication to `resolve_variant_files()` (tracks seen src/dest pairs and shared paths)
- [x] ~~Extract shared manifest options~~ — deferred. The duplication is 3 identical option blocks across 2 files. Extraction would add loading complexity for minimal benefit.
- [x] Add `govkit init` command (creates feature folder from starter, with interactive type prompt and next-steps guidance)

### 4.4 Test Suite for govkit
- [x] Create `tests/` directory with pytest setup
- [x] Tests for `copy_entry()`, `resolve_options()`, `resolve_variant_files()`, `load_manifest()`
- [x] Tests for all `validate.py` check functions
- [x] Add test dependencies to `pyproject.toml`

---

## Working Agreement

- Each checked item = one atomic commit
- Related items within a subsection may be combined into a single commit if they touch the same files
- Commit format: `fix:` / `feat:` / `docs:` as appropriate
- Work proceeds top-down (Tier 1 before Tier 2, etc.) unless dependencies require reordering
- This file is updated as work progresses
