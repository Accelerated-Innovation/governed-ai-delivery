# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
