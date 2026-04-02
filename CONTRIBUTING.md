# Contributing to Governed AI Delivery

Thank you for your interest in improving govkit. This document explains how to contribute.

---

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/<your-username>/governed-ai-delivery.git`
3. Install in development mode: `pip install -e .`
4. Run the CLI: `govkit list`

---

## Project Structure

```
agents/         — Agent configurations (Claude Code, Copilot) installed into target projects
cli/            — govkit CLI (govkit.py, validate.py)
docs/           — Architecture contracts and evaluation standards
features/       — Feature starters and worked examples
governance/     — JSON Schemas and templates
ci/             — CI pipeline templates (GitHub Actions, Azure DevOps)
tests/          — Test suite (pytest)
```

---

## Common Contributions

### Adding a New Agent

1. Create `agents/<agent-name>/manifest.json` following the existing schema
2. Create the agent's configuration files (instructions, rules, prompts)
3. Add variant support (type, ui, ci) matching existing agents
4. Test with `govkit apply --agent <agent-name> --target <test-dir>`
5. Update the README's "Supported Agents" table

### Modifying Architecture Docs

Architecture documents in `docs/` are the source of truth for AI agents. Changes should be:
- Consistent with existing patterns (hexagonal architecture, MVVM)
- Accompanied by an ADR if introducing a new pattern
- Reflected in agent rules/instructions if they affect code generation

### Modifying Schemas

Schemas in `governance/` validate feature artifacts. When changing a schema:
- Ensure backward compatibility (or document the breaking change)
- Update the corresponding starter templates
- Update worked examples to match the new schema

### Modifying CI Pipelines

CI templates in `ci/` are installed into target projects. Changes should be:
- Applied to both GitHub Actions and Azure DevOps versions
- Documented in `ci/README.md`
- Tested against the worked examples

---

## Commit Format

```
type(scope): description

Types: feat, fix, docs, test, refactor, chore
```

Examples:
- `feat: add new agent type for cursor`
- `fix: correct JSON schema validation for mode: none`
- `docs: add troubleshooting section to README`

---

## Pull Request Process

1. Create a branch from `main`
2. Make your changes with atomic commits
3. Ensure `govkit validate` passes against worked examples
4. Open a PR with a clear description of what changed and why
5. Link any related issues

---

## Code Style

- Python: follow `ruff` defaults (configured in `pyproject.toml`)
- Markdown: ATX headings (`#`), fenced code blocks, tables where appropriate
- YAML: 2-space indentation, no trailing whitespace

---

## Questions?

Open an issue at [github.com/Accelerated-Innovation/governed-ai-delivery/issues](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues).
