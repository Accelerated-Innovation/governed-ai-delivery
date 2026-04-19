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
agents/         Agent configurations installed into target projects
cli/            govkit CLI commands and validation logic
docs/           Architecture contracts, guidance, and reference material
features/       Feature starters and worked examples
governance/     JSON Schemas and templates
ci/             CI pipeline templates
tests/          Test suite
````

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

