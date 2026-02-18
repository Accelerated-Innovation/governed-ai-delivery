# 🚧 Project Overview

This template accelerates delivery of spec-driven, architecture-governed AI-powered features using GitHub Copilot.

Each feature integrates:

- **Gherkin** for acceptance criteria
- **NFRs** for system-level constraints
- **LLM eval criteria** for agent behavior
- **Copilot Chat** for planning, code generation, and compliance
- **CI gates** for testing, linting, architectural rules, and eval validation

---

## ⚡️ Quickstart

1. Create a repo using this template:
   ```bash
   gh repo create my-new-project --template <this-repo>
   ```

2. Create a feature folder:
   ```
   features/my_feature/
     ├─ my_feature.feature
     ├─ nfrs.md
     └─ eval_criteria.yaml
   ```

3. Open in VS Code and install tooling:
   ```bash
   pip install -r requirements.txt
   pre-commit install
   ```

4. Enable GitHub Copilot Chat (with plan + agent mode).

---

## 🌝 Feature Workflow

Assumes this structure:
```
features/cool_feature/
  ├─ cool_feature.feature
  ├─ nfrs.md
  └─ eval_criteria.yaml
```

### Steps

1. Open repo in VS Code.
2. Switch Copilot Chat to **Plan** mode.
3. Run:
   ```
   /architecture-preflight
   ```
4. Provide:
   - Feature name: `cool_feature`
   - Paths to:
     - `features/cool_feature/nfrs.md`
     - `features/cool_feature/cool_feature.feature`
     - `features/cool_feature/eval_criteria.yaml`

5. Review the preflight output.
6. If flagged, run `/adr-author` to generate an ADR.
7. Commit ADR to `docs/architecture/ADR/`.
8. Switch Copilot to **Agent** mode.
9. Run:
   ```
   /implementation-plan
   ```
10. Review or edit the plan.
11. Start implementation with Copilot.
12. Review and commit the code.
13. Push branch and open PR.
14. CI runs:
    - Unit, integration, and contract tests
    - SonarQube and import-linter rules
    - LLM eval checks (if defined)
15. Confirm:
    - Plan was followed
    - Specs are covered
    - ADR submitted (if required)
16. Merge on passing checks and approvals.

---

## 🏗 Architecture

- [`ARCH_CONTRACT.md`](docs/architecture/ARCH_CONTRACT.md)
- [`BOUNDARIES.md`](docs/architecture/BOUNDARIES.md)
- [`API_CONVENTIONS.md`](docs/architecture/API_CONVENTIONS.md)
- [`SECURITY_AUTH_PATTERNS.md`](docs/architecture/SECURITY_AUTH_PATTERNS.md)

---

## 🧱 Structure

- `api/` — FastAPI HTTP layer (inbound adapter)
- `ports/` — inbound/outbound interfaces
- `services/` — business logic (domain core)
- `repos/` — persistence + integration adapters
- `common/` — shared types and utils

---

## 🔐 Security

- JWT auth and RBAC enforced at API layer
- See `SECURITY_AUTH_PATTERNS.md`

---

## ⚙️ Configuration

- All secrets must use env vars via `BaseSettings`

---

## ✅ Testing

> *TODO: Add test entry points and coverage requirements.*

---

## 🤝 Contributing

- Follow all `docs/architecture/**` standards
- Submit ADR for changes to:
  - Layering or module boundaries
  - Security/auth behavior
  - External dependencies

---

## 📄 License

> *TODO: Add license details if needed.*

---

## Copilot Prompts explained

[Watch on YouTube](https://youtu.be/0XoXNG65rfg?si=sWwyYr84zgNr5mRz)

