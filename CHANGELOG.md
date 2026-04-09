# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.4.0] — 2026-04-09

### Added
- **Level 5: GenAI Operations** — governed tooling for LLM-powered features
- **Architecture contracts** — LLM_GATEWAY_CONTRACT.md (LiteLLM), OBSERVABILITY_LLM_CONTRACT.md (OpenLLMetry + Langfuse), GUARDRAILS_CONTRACT.md (NeMo + Guardrails AI), EVALUATION_LLM_CONTRACT.md (DeepEval + Promptfoo + RAGAS)
- **Practical guides** — 8 usage guides in `docs/backend/guides/` (one per tool)
- **Guardrails config schema** — `governance/backend/schemas/guardrails_config.schema.json`
- **L5 feature starters** — `starter_backend_l5/`, `starter_cli_l5/` with LLM NFRs, deepeval criteria, L5 preflight sections
- **L5 plan and preflight templates** — extended with LLM gateway, guardrails, and evaluation sections
- **L5 agent rules** — `llm-gateway.md`, `guardrails.md`, `llm-evaluation.md`, `llm-observability.md` (Claude Code + Copilot)
- **L5 agent skills** — `/genai-preflight` (validates L5 architecture decisions), `/eval-suite-planning` (plans DeepEval/Promptfoo/RAGAS suites)
- **L5 CI templates** — `deepeval-gate.yml`, `promptfoo-gate.yml`, `guardrails-check.yml` (GitHub Actions + Azure DevOps)
- **L5 CLAUDE.md variants** — `l5-backend-api.md`, `l5-backend-cli.md`
- **L5 Copilot instruction variants** — `l5-backend-api.md`, `l5-backend-cli.md`
- **L5 validation checks** — `check_llm_nfrs()`, `check_l5_eval_criteria()`, `check_l5_preflight_sections()` (9 total checks at L5)

### Changed
- **eval_criteria.schema.json** — added 11 new eval_class values (deepeval_*, promptfoo_*, ragas_*) and optional `tool` field
- **evaluation_prediction.schema.json** — added optional `llm_evaluation` object for L5 predictions
- **agent-manifest.schema.json** — added `level_5` to variant_config properties
- **TECH_STACK.md** — added sections for LLM Gateway, LLM Evaluation, LLM Observability, Runtime Guardrails
- **AGENT_ARCHITECTURE.md** — updated tool integration, observability, evaluation, added guardrails section
- **EVAL_STACK.md** — replaced LangSmith/Arize with Langfuse, added DeepEval/Promptfoo/RAGAS
- **check_gherkin_nfr_coverage()** — now skips non-standard NFR categories (e.g., LLM-specific)
- **CLI** — `--level` accepts "5", `cmd_init` selects L5 starters, marker version bumped to 0.4.0

---

## [0.3.0] — 2026-04-08

### Added
- **Maturity model** — govkit now supports Level 3 (Spec-Driven Development) and Level 4 (Governed AI Delivery)
- **`--level` flag** — `govkit apply`, `govkit init`, and `govkit validate` accept `--level 3` or `--level 4`
- **`.govkit` marker file** — written after `govkit apply`, tracks level and options for auto-detection by `init` and `validate`
- **Level 3 feature starters** — `starter_backend_l3/`, `starter_cli_l3/`, `starter_ui_l3/` with 3 artifacts (no eval_criteria.yaml, no architecture_preflight.md)
- **Level 3 plan templates** — simplified plan.md without evaluation_prediction blocks
- **Level 3 generic agent rules** — `test-first.md` and `spec-compliance.md` (no path-scoped rules)
- **Level 3 CLAUDE.md variants** — `l3-backend-api.md`, `l3-backend-cli.md`, `l3-ui-react.md`, `l3-ui-angular.md`
- **Level 3 agent skills** — simplified `/spec-planning` and `/implementation-plan` without evaluation scoring
- **Level 3 Copilot equivalents** — L3 copilot-instructions and prompts for all project types
- **Level 3 CI templates** — `l3-quality-gate.yml` for GitHub Actions and Azure DevOps (no eval gates, no boundary checks)
- **Level-aware validation** — `govkit validate` checks 3 artifacts for L3, 5 for L4; skips eval checks at L3
- **Manifest `level_3` sub-key** — variant overrides co-located with parent variants; schema updated

### Changed
- **Manifest schema** — `variant_config` now accepts optional `level_3` override with same shape
- **`resolve_variant_files()`** — respects level selection, uses `level_3` override when level is "3"
- **`run_validation()`** — accepts `level` parameter; auto-detects from `.govkit` marker
- **`check_completeness()`** — parameterized to accept custom artifact list
- **Starter skip list** — includes L3 starters (`starter_backend_l3`, etc.)

---

## [0.2.0] — 2026-04-02

### Added
- **FIRST Scoring Rubric** — concrete 1–5 scoring definitions for each FIRST principle (backend and UI)
- **7 Virtues Scoring Rubric** — concrete 1–5 scoring definitions for each code virtue (backend and UI)
- **Observability Port Contract** — port interface, adapter example, and testing guidance
- **Error Mapping Contract** — domain exception hierarchy and HTTP status mapping
- **Cross-Cutting Concerns** — DTOs, validation boundaries, pagination, timestamps, soft deletes, audit trails, configuration
- **LangGraph vs LangChain decision matrix** in TECH_STACK.md
- **Evaluation prediction schema** — JSON Schema for plan.md prediction blocks
- **Import-linter reference config** — ready-to-merge config for hexagonal architecture enforcement
- **CI governance artifact checks** — jobs to verify architecture preflight exists and commit message format
- **CI README** — documents what's enforced vs predicted vs stubbed vs agent-only
- **README expansion** — prerequisites, concepts, interactive prompt example, post-install verification, troubleshooting, FAQ, glossary, governance structure explanation
- **CONTRIBUTING.md** and **CHANGELOG.md**

### Changed
- **Evaluation prediction format standardized** — UI now uses same `first`/`virtues`/`accessibility` structure as backend
- **UI eval-gate** now checks Virtue scores in addition to FIRST scores (GitHub Actions + Azure DevOps)
- **Copilot prompts enhanced** — added template locations, output paths, scoring rubric references, increment sizing
- **Starter templates** — added mode selection instructions to backend and CLI starters
- **Skill invocation syntax** — corrected `/project:` prefix to `/` in README and all CLAUDE.md variants

### Fixed
- **CLI error handling** — source path validation, UTF-8 encoding, JSON parse error handling, manifest structure validation
- **`cmd_list`** — now skips non-directory entries and handles malformed manifests gracefully

---

## [0.1.0] — 2026-04-01

### Added
- Initial release
- Two agents: `claude-code` and `copilot` with variant-based manifests
- Variant options: `--type` (api/cli), `--ui` (none/react/angular), `--ci` (github/azure)
- CLI: `govkit apply`, `govkit list`, `govkit validate`
- Backend architecture docs: ARCH_CONTRACT, BOUNDARIES, API_CONVENTIONS, CLI_CONVENTIONS, SECURITY_AUTH_PATTERNS, TECH_STACK, TESTING, DESIGN_PRINCIPLES, GHERKIN_CONVENTIONS
- UI architecture docs: MVVM_CONTRACT, COMPONENT_CONVENTIONS, STATE_MANAGEMENT (React + Angular)
- Evaluation standards: eval_criteria.md (backend + UI), EVAL_STACK.md
- Feature starters: starter_backend, starter_cli, starter_ui
- Worked examples: schema_contract_example, ui_task_dashboard
- CI templates: quality-gate, eval-gate, ui-quality-gate, ui-eval-gate (GitHub Actions + Azure DevOps)
- Governance schemas: eval_criteria.schema.json (backend + UI)
