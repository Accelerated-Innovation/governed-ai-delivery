# Contributing to Governed AI Delivery

Thank you for your interest in improving GovKit. This document explains how to contribute.

---

## Contribution Guidelines

Please keep changes focused and easy to review.

For significant changes, open an issue first so the proposal can be discussed before implementation begins.

When a change affects behavior, contributors should update the relevant documentation, templates, examples, schemas, and tests in the same pull request where applicable.

---

## Getting Started

### External contributors

1. Fork the repository
2. Clone your fork: `git clone https://github.com/<your-username>/governed-ai-delivery.git`
3. Create a branch for your change
4. Install in development mode: `pip install -e ".[dev]"`
5. Run the CLI: `govkit list`

### Maintainers

1. Clone the repository
2. Create a branch from `main`
3. Install in development mode: `pip install -e ".[dev]"`
4. Run the CLI: `govkit list`

---

## Project Structure

```text
governed-ai-delivery/
├── agents/
│   ├── claude-code/                  # Claude Code agent (variant-based)
│   │   ├── manifest.json            # Variant options: level, type, ci (v0.8 — no more `ui`)
│   │   ├── claude-md/               # CLAUDE.md variants per project shape (api, cli, ui-react, ui-angular)
│   │   ├── rules/                   # Path-scoped rules (backend/, cli/, ui-react/, ui-angular/, generic/)
│   │   └── skills/                  # Open Skills format (backend/, ui/) — installed to .claude/skills/
│   ├── copilot/                     # Copilot agent (variant-based)
│   │   ├── manifest.json
│   │   ├── copilot-instructions/    # .github/copilot-instructions.md variants per shape
│   │   ├── instructions/            # Path-scoped instructions with applyTo: globs (backend/, cli/, ui-react/, ui-angular/, generic/)
│   │   └── skills/                  # Open Skills format — installed to .github/skills/
│   └── codex/                       # OpenAI Codex agent (variant-based)
│       ├── manifest.json
│       ├── agents-md/               # Root AGENTS.md variants per shape and level
│       ├── rules/                   # Body-only rules installed as nested AGENTS.md per layer
│       └── skills/                  # Open Skills format — installed to .agents/skills/
├── cli/
│   ├── govkit.py                    # CLI — apply, list, init, validate
│   └── validate.py                  # Governance compliance checker
├── docs/
│   ├── backend/
│   │   ├── architecture/            # ARCH_CONTRACT, BOUNDARIES, API_CONVENTIONS, ADR/, etc. (L3+)
│   │   ├── evaluation/              # eval_criteria.md, FIRST/Virtue scoring rubrics (L4+)
│   │   └── guides/                  # Level 5 tool setup guides (LiteLLM, DeepEval, etc.)
│   ├── ui/
│   │   ├── architecture/
│   │   │   ├── MVVM_CONTRACT.md
│   │   │   ├── react/               # COMPONENT_CONVENTIONS, STATE_MANAGEMENT, TECH_STACK
│   │   │   └── angular/             # COMPONENT_CONVENTIONS, STATE_MANAGEMENT, TECH_STACK
│   │   └── evaluation/              # UI eval_criteria.md, FIRST/Virtue rubrics
│   └── stacks/                      # Stack-specific architecture doc overrides
│       ├── dotnet-aspnet/
│       ├── java-spring-boot/
│       ├── nodejs-fastify/
│       └── go-gin/
├── features/                        # bundled with govkit, scaffolded by `govkit init` at L4+
│   ├── starter_backend/             # API backend starter (Level 4 Spec-Driven Add-On, 5 artifacts)
│   ├── starter_cli/                 # CLI project starter
│   ├── starter_ui/                  # UI starter
│   └── (worked examples)
├── governance/
│   ├── backend/schemas/             # eval_criteria.schema.json, guardrails_config.schema.json
│   ├── schemas/                     # evaluation_prediction.schema.json
│   └── ui/schemas/                  # UI eval_criteria.schema.json
├── ci/
│   ├── github/                      # GitHub Actions CI templates
│   └── azure/                       # Azure DevOps CI equivalents
└── tests/                           # pytest test suite for govkit CLI
```

---

## Common Contributions

### Adding a New Agent

1. Create `agents/<agent-name>/manifest.json` following the existing schema
2. Add the agent configuration files such as instructions, rules, and prompts
3. Add any required variant support
4. Test with `govkit apply --agent <agent-name> --target <test-dir>`
5. Update the README's supported agents section

### Modifying Architecture Docs

Documents in `docs/` are a source of truth for agent behavior and generated project structure.

Changes should:

* Stay consistent with current architectural guidance
* Include an ADR when introducing or changing a significant pattern
* Be reflected in related agent instructions, templates, or examples when they affect generated output
* Avoid placing stack-specific rules in generic guidance unless intentionally scoped

### Modifying Skills (Open Skills Format)

All `SKILL.md` files across the three agents follow the **Open Skills** standard:

```yaml
---
name: <skill-name>
description: <one sentence describing WHAT the skill does AND WHEN to use it. The harness uses this to decide whether to invoke.>
---

<body — operates on natural-language arguments derived from context; no $ARGUMENTS substitution>
```

When modifying or adding a skill:

* **Frontmatter must be byte-identical** across all three agents for the same skill (e.g., `agents/{claude-code,codex,copilot}/skills/backend/spec-planning/SKILL.md` must share the same `name:` and `description:`). The parity test in `tests/test_govkit.py::TestNoUiDimensionInManifests` and the test suite generally lock this in.
* **No `$ARGUMENTS` substitution** — derive feature names and other arguments from the user's natural-language request; ask if not provided.
* **No agent-specific extensions** like `argument-hint:` (Claude Code) or `user-invocable:` (Copilot) — these were removed in v0.8.
* **Body content can differ slightly** between agents only in path-notation conventions (e.g., Copilot uses `**` globs; Codex references nested `AGENTS.md` paths). The substantive instructions must match.
* For Codex's root files (`agents-md/*.md`), use `$skill-name` invocation syntax (Codex-native). For Claude Code (`claude-md/*.md`) and Copilot (`copilot-instructions/*.md`), use `/skill-name`.

If you add a new skill, ship it for all three agents in lockstep. The test suite enforces parity.

### Modifying Schemas

Schemas in `governance/` validate feature artifacts. When changing a schema:

* Preserve backward compatibility where possible
* Document breaking changes clearly when not possible
* Update the corresponding starter templates
* Update worked examples to match the revised schema

### Modifying CI Pipelines

CI templates in `ci/` are installed into target projects. Changes should:

* Be applied consistently across supported CI platforms where relevant
* Be documented in `ci/README.md`
* Be tested against worked examples or a representative target project

---

## Commit Format

```text
type(scope): description
```

Types:

* `feat`
* `fix`
* `docs`
* `test`
* `refactor`
* `chore`

Examples:

* `feat: add new agent type for cursor`
* `fix: correct JSON schema validation for mode: none`
* `docs: add troubleshooting section to README`

---

## Validation Before Opening a PR

Before submitting a pull request:

1. Run relevant tests
2. Run `govkit validate` against worked examples where applicable
3. Update documentation if behavior or structure changed
4. Update templates, schemas, and examples together when required
5. Confirm the change is limited to one logical scope

---

## Pull Request Process

1. Create a branch from `main`
2. Keep the pull request focused on one logical change
3. Make your changes with clear, atomic commits
4. Run validation and relevant tests before opening the PR
5. Link any related issues
6. Open a PR with a clear description of what changed and why

---

## Code Style

* Python: follow `ruff` defaults as configured in `pyproject.toml`
* Markdown: use ATX headings and fenced code blocks
* YAML: use 2-space indentation and avoid trailing whitespace

---

## Questions and Security Reports

For bugs, questions, or feature requests, open an issue at [github.com/Accelerated-Innovation/governed-ai-delivery/issues](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues).

For security-related concerns, do not open a public issue. Follow the instructions in `SECURITY.md`.

