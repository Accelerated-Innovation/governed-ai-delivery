# Governed AI Delivery — Improvement Plan

> Generated 2026-04-02 from a comprehensive expert review of the entire project.
> This plan is the single source of truth for tracking improvement work.
> Each increment is designed to be atomic and independently committable.

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
- [ ] Update README to reference mode selection in starters

### 1.5 Prediction vs Actual CI Gap
- [x] Document the approach in `ci/README.md` (what's enforced now vs predicted vs stubbed vs agent-only)
- [x] ~~Add placeholder CI jobs~~ — stubs already exist with clear "Configure your..." guidance. CI README now documents how to close each gap.
- [ ] Design approach for post-implementation CI jobs that compare actual test/lint/accessibility results to plan.md predictions (deferred — requires team-specific tooling)

---

## Tier 2 — Significant Gaps (incomplete governance)

### 2.1 Agent/CI Enforcement Alignment
- [ ] Add CI job: check `features/*/architecture_preflight.md` exists for any feature with a plan.md
- [ ] Add CI job: validate commit message format `feat|fix|docs|test(<scope>): ...`
- [ ] Document which governance checks are agent-side vs CI-side in a single reference table

### 2.2 Evaluation Prediction Format Alignment
- [ ] Standardize evaluation_prediction YAML schema (document exact structure)
- [ ] Align Copilot UI prompts to match the CI-expected format
- [ ] Align Claude Code UI skills to match the same format
- [ ] Add the schema to `governance/schemas/evaluation_prediction.schema.json`

### 2.3 Missing Architecture Artifacts
- [ ] Create `docs/backend/architecture/OBSERVABILITY_PORT_CONTRACT.md` (port interface definition)
- [ ] Create `docs/backend/architecture/ERROR_MAPPING.md` (domain exceptions to HTTP status codes)
- [ ] Create `docs/backend/architecture/CROSS_CUTTING_CONCERNS.md` (DTOs, validation boundaries, audit trails)
- [ ] Add LangGraph vs LangChain decision matrix to `TECH_STACK.md` Section 4

### 2.4 Import-Linter Config
- [ ] Create reference `.importlinter` config for Python hexagonal architecture
- [ ] Add to `agents/claude-code/manifest.json` as a shared artifact
- [ ] Add to `agents/copilot/manifest.json` as a shared artifact

### 2.5 Copilot Prompt Parity
- [ ] Enhance `adr-author.prompt.md` to match Claude Code skill detail (template location, required sections)
- [ ] Enhance `spec-planning.prompt.md` with explicit eval_criteria structure
- [ ] Enhance `implementation-plan.prompt.md` with increment sizing guidance
- [ ] Enhance `architecture-preflight.prompt.md` with section requirements

### 2.6 Backend vs UI Evaluation Harmonization
- [ ] Add Virtue scoring check to UI eval-gate (both GitHub Actions and Azure DevOps)
- [ ] Document why backend and UI gates differ (if intentional) or align them

---

## Tier 3 — Documentation & DX

### 3.1 README Expansion
- [ ] Add Prerequisites & System Requirements section
- [ ] Add post-install verification section (what the target project should look like)
- [ ] Add Concepts section before Quickstart (hexagonal architecture, FIRST, Gherkin, governance — brief)
- [ ] Add concrete end-to-end walkthrough example
- [ ] Add Troubleshooting & FAQ section (8-12 entries)
- [ ] Add interactive prompt example output for `govkit apply`
- [ ] Add Interpreting Validation Failures section

### 3.2 Terminology & Glossary
- [ ] Add glossary to README or create `docs/GLOSSARY.md` (agent, rule, skill, instruction, prompt, port, adapter, domain, evaluation, FIRST, 7 Virtues)
- [ ] Clarify distinction between `/architecture-preflight` (skill) and `govkit validate` (CLI)

### 3.3 Supporting Documents
- [ ] Create `CONTRIBUTING.md` (how to add agents, modify schemas, test, PR process)
- [ ] Create `CHANGELOG.md` (starting from current 0.1.0)
- [ ] Add "Getting Help" section to README

### 3.4 Governance Structure Explanation
- [ ] Add section to README explaining `docs/` vs `governance/` vs `features/` separation

---

## Tier 4 — Polish & Hardening

### 4.1 Schema & Validation Tightening
- [ ] Add `eval_class` enum to `governance/backend/schemas/eval_criteria.schema.json`
- [ ] Create `governance/schemas/agent-manifest.schema.json` for manifest validation
- [ ] Add Scenario Outline guidance to Gherkin conventions doc

### 4.2 CI Hardening
- [ ] Make bundle-size check blocking (remove `continue-on-error: true`) or document why advisory
- [ ] Remove duplicate schema validation (runs in both quality-gate and eval-gate)
- [ ] Add SonarQube/Snyk configuration templates or document them as optional with graceful skip

### 4.3 CLI Polish
- [ ] Add deduplication to `resolve_variant_files()`
- [ ] Extract shared manifest options to avoid DRY violation across agents
- [ ] Add `govkit init` or feature scaffolding command (creates feature folder with correct starter)

### 4.4 Test Suite for govkit
- [ ] Create `tests/` directory with pytest setup
- [ ] Tests for `copy_entry()`, `resolve_options()`, `resolve_variant_files()`, `load_manifest()`
- [ ] Tests for all `validate.py` check functions
- [ ] Add test dependencies to `pyproject.toml`

---

## Working Agreement

- Each checked item = one atomic commit
- Related items within a subsection may be combined into a single commit if they touch the same files
- Commit format: `fix:` / `feat:` / `docs:` as appropriate
- Work proceeds top-down (Tier 1 before Tier 2, etc.) unless dependencies require reordering
- This file is updated as work progresses
