# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.7.0] — 2026-05-08

### Breaking changes — maturity model reframed

The meaning of Level 3 and Level 4 has changed. **If your project's `.govkit` marker says `level: "3"` or `level: "4"`, please read this section before upgrading.**

| Level | v0.6.x | v0.7.0 |
|---|---|---|
| **L3** | Spec-Driven Development (3 artifacts per feature) | **Governed AI Delivery (Foundations)** — agent rules + architecture docs only; no `features/` directory |
| **L4** | Governed AI Delivery (5 artifacts per feature) | **Spec-Driven Add-On** — adds `features/` and the 5-artifact contract on top of L3 |
| **L5** | GenAI Operations | GenAI Operations *(unchanged)* |

The new model is additive (L4 ⊃ L3) and splits at a clearer boundary: whether your project adopts a `features/` directory model.

### What this means for adopters

After upgrading, govkit prints a one-time stderr migration warning per command invocation until you run `govkit upgrade --migrate-levels`. Suppress with `GOVKIT_NO_MIGRATION_WARNING=1` if needed.

**If your marker says `level: "3"`** (3-artifact features under v0.6.x):

Your project's shape (a `features/` directory with 3-artifact dirs) maps most closely to the new **L4**, but L4 requires 5 artifacts per feature. Run `govkit upgrade --migrate-levels` for an interactive prompt with four options:

1. Migrate to L4 with stub generation — govkit creates `eval_criteria.yaml` and `architecture_preflight.md` stubs in each feature dir; you fill them in over time. Stubs use TBD placeholders that will fail validation until completed.
2. Migrate to L4 without stubs — you author the two new artifacts manually. Validation will fail until you do.
3. Adopt new-L3 (Foundations) — you confirm we should DELETE your `features/` directory and switch to architecture-only governance (no per-feature artifacts).
4. Abort — pin `govkit==0.6.*` in your project until you're ready.

**If your marker says `level: "4"`** (5-artifact features under v0.6.x):

No data migration needed. Your project shape is correct under v0.7.0; only the level label flips from "Governed AI Delivery" to "Spec-Driven Add-On". Run `govkit upgrade --migrate-levels` to clear the migration warning.

**If your marker says `level: "5"`:**

Nothing changes for you. Run `govkit upgrade --migrate-levels` to clear the migration warning.

### Changed
- **CLI default level** — `govkit apply` now defaults to `--level 3` (was `4`). Three agent manifests' `options.level.default` flipped to `"3"`.
- **`govkit init` at L3 errors** — points to `govkit apply --level 4` (Foundations has no `features/` directory model).
- **`govkit validate` at L3 is a no-op** — returns 0 with informational message (Foundations has no per-feature artifacts; CI quality-gate is the L3 compliance surface).
- **`govkit apply --level 3`** — no longer creates an empty `features/` directory in the target.
- **Manifest schema** — `level_3` key removed; `level_4` key added with optional `mode: "merge" | "replace"`. Default mode for `level_4` is `"merge"`; for `level_5` is `"replace"`. The `governed` array property is now formally allowed (previously the schema rejected it despite all live manifests using it — a long-standing schema bug, fixed here).
- **L3 CI gate** (`l3-quality-gate.yml`) rewritten as a lean codebase-wide gate: commit-format, import-linter (architecture boundaries), SonarQube, Snyk. No per-feature artifact checks.
- **Test-first and spec-compliance rules** (`test-first.md`, `spec-compliance.md`) move from L3 to L4. They are still part of the kit; they are now part of the spec-driven add-on (binding rather than recommended).

### Added
- **`govkit upgrade --migrate-levels`** — interactive marker migration for v0.6.x → v0.7.0 maturity model swap.
- **One-time migration warning** — `read_govkit_marker` emits a stderr warning when `version < "0.7.0"`. Suppressible via `GOVKIT_NO_MIGRATION_WARNING=1`. Auto-suppressed once the marker is rewritten to `0.7.0+`.
- **L4 add-on manifest blocks** with `mode: "merge"` semantics — `level_4` entries layer additively over the L3 base, with `dest`-collision resolution preferring the override (used to swap `CLAUDE.md` / `AGENTS.md` / `.github/copilot-instructions.md` between L3 and L4 modes).
- **Twelve new L3 entry-point instruction files** (4 per agent × 3 agents) — Foundations content focused on architecture-aware development without per-feature artifacts. Existing v0.6 governed instructions preserved at `l4-*.md` paths.
- **`tests/test_maturity_model.py`, `tests/test_schemas.py`, `tests/test_l3_instructions.py`** — 200+ new tests locking in the model.

### Removed
- `features/starter_{backend,cli,ui}_l3/` — 3-artifact starters (the new L3 has no `features/` model).
- `governance/{backend,ui}/templates/l3-plan.md` — L3 has no plan.md artifact.
- `agents/<a>/skills/<area>/l3-{spec-planning,implementation-plan}/` — replaced by the L4 add-on skills (which now ship at L4 instead of being level-specific).
- `agents/<a>/<inst>/l3-{backend-api,backend-cli,ui-react,ui-angular}.md` — superseded by the new L3 entry-point files (current top-level paths) and the renamed `l4-*.md` files (preserved L4 content).

### Support and pinning

- v0.6.x will receive bug-fix-only backports through the v0.8.0 release.
- Pin with `pip install govkit==0.6.*` if you want to defer the migration.

### Migration commands

```bash
pip install --upgrade govkit
govkit upgrade --migrate-levels --target /path/to/your/project
```

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
