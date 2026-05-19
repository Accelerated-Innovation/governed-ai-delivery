# Monorepo Pattern — One Repo, Multiple Shapes

govkit v0.8's flat `--type` model treats each install as **one project shape**: backend (`api` / `cli`) or UI (`ui-react` / `ui-angular`). The cross-product UI sidecar from v0.7 is gone — there's no "fullstack" shape.

For teams that need both backend and UI in the same repository, the supported pattern is **one `govkit apply` per subdirectory** of a monorepo. Each subdir becomes a complete, self-contained govkit install. The three agents all support subpath governance natively — no install-time changes required.

---

## When to use this pattern

Use the monorepo pattern when:

- A backend service and its dedicated UI ship in the same git repository
- The team wants distinct governance for each shape (backend's hexagonal model vs UI's MVVM model) without one set of rules bleeding into the other
- CI gates need to differ between the backend and UI portions (the backend gates target Python/Go/Java; the UI gates target Node/TypeScript)

**Don't use this pattern** if:

- The backend and UI live in separate repositories — use a separate `govkit apply --type ...` in each repo. See [CROSS_REPO_FEATURES.md](docs/CROSS_REPO_FEATURES.md) for cross-repo coordination.
- The project is single-shape (backend-only or UI-only) — use a single root-level `govkit apply` and skip this pattern entirely.

---

## Directory layout

```
my-monorepo/
├── apps/
│   ├── api/                   # govkit-installed backend shape
│   │   ├── CLAUDE.md          # (or AGENTS.md / .github/copilot-instructions.md)
│   │   ├── .claude/
│   │   ├── docs/backend/
│   │   ├── governance/backend/
│   │   ├── features/          # backend feature artifacts
│   │   ├── ci/github/         # backend CI gates
│   │   ├── services/
│   │   ├── ports/
│   │   └── adapters/
│   └── web/                   # govkit-installed UI shape
│       ├── CLAUDE.md
│       ├── src/CLAUDE.md      # Claude UI nested layer rules
│       ├── .claude/
│       ├── docs/ui/
│       ├── governance/ui/
│       ├── features/          # UI feature artifacts
│       ├── ci/github/         # UI CI gates
│       └── src/
│           ├── features/
│           └── shared/
├── packages/                  # optional — shared libraries (no govkit install)
└── README.md
```

Each `apps/<shape>/` install is independent: separate `.govkit` marker, separate `features/`, separate CI gates, separate `docs/`. Re-applying or upgrading one does not touch the other.

---

## Install commands

```bash
# Backend
govkit apply --agent claude-code --type api --level 4 --ci github --target apps/api

# React UI
govkit apply --agent claude-code --type ui-react --level 4 --ci github --target apps/web

# Or use a different agent per app if your team mixes them
govkit apply --agent codex   --type api      --level 4 --ci github --target apps/api
govkit apply --agent copilot --type ui-react --level 4 --ci github --target apps/web
```

`--target` accepts any path. The relative path you point at becomes the install root for that shape.

---

## How each agent picks up the right rules

The three agents have different rule-loading mechanisms, but all three respect a directory-rooted install when you point them at a subpath.

### Claude Code

Claude Code recursively discovers `CLAUDE.md` files by walking from the open file up to the workspace root. When you open a file under `apps/api/`, Claude reads `apps/api/CLAUDE.md` (backend rules). When you open a file under `apps/web/`, Claude reads `apps/web/CLAUDE.md` (UI rules), plus the nested `apps/web/src/CLAUDE.md` when working under `src/`.

To get this behavior:

- **Open the monorepo root** (`my-monorepo/`) in Claude Code, OR
- **Open just the app directory** (`apps/api/` or `apps/web/`) as a separate workspace — recommended for sharp separation

Path-scoped layer rules (`.claude/rules/*.md`) under each app are also automatically scoped to that app's tree.

### Codex

Codex walks up from the file being edited to the nearest `AGENTS.md` and concatenates each one it finds along the way. With per-subdir installs:

- A file under `apps/api/services/` resolves to: `apps/api/services/AGENTS.md` (if present) → `apps/api/AGENTS.md` → `AGENTS.md` (root, if you write one for monorepo-wide context)
- A file under `apps/web/src/features/login/components/` resolves to: `apps/web/src/features/components/AGENTS.md` → `apps/web/src/AGENTS.md` → `apps/web/AGENTS.md` → `AGENTS.md` (root)

The natural hierarchical loader means **no extra wiring is required** — Codex finds the right rules from the file path alone.

If you want a monorepo-wide root `AGENTS.md` (e.g., describing the monorepo conventions, shared tooling, branching strategy), author it manually at the repo root; govkit doesn't generate one. Keep it short and let the per-app `AGENTS.md` files own the shape-specific governance.

### Copilot

Copilot scopes instructions via the `applyTo:` glob in each `.instructions.md` file's frontmatter. The govkit-installed instructions under `apps/api/.github/instructions/` are scoped to backend-shape globs (`**/services/**`, `**/adapters/**`, etc.). The instructions under `apps/web/.github/instructions/` are scoped to UI-shape globs (`src/**/components/**/*.tsx`, etc.).

**One adjustment is required for Copilot monorepos**: the `applyTo:` globs are relative to the workspace root, not the install dir. If Copilot's workspace root is the monorepo root (`my-monorepo/`), the default globs are too broad — `**/services/**` would match `apps/web/src/services/` (a UI directory) by accident.

After running `govkit apply` per subdir, tighten each `applyTo:` glob to prefix the app path:

```yaml
# apps/api/.github/instructions/services.instructions.md
---
applyTo: "apps/api/**/services/**"
---
```

```yaml
# apps/web/.github/instructions/components.instructions.md
---
applyTo: "apps/web/src/**/components/**/*.tsx"
---
```

A one-line `sed` or a small script can do the prefix swap across all installed instruction files. Future govkit versions may automate this via a `--monorepo-prefix` flag — for now, do it once after `apply` per app.

---

## CI in a monorepo

Each shape's CI gates live under `apps/<shape>/ci/<provider>/`. There are two practical ways to wire them into your repo's CI:

**Option A — Path-filtered workflows (recommended for GitHub Actions).** One workflow file per shape, each gated on `paths:`:

```yaml
# .github/workflows/backend-quality-gate.yml
on:
  pull_request:
    paths: ["apps/api/**"]
jobs:
  backend:
    uses: ./apps/api/ci/github/quality-gate.yml
```

```yaml
# .github/workflows/ui-quality-gate.yml
on:
  pull_request:
    paths: ["apps/web/**"]
jobs:
  ui:
    uses: ./apps/web/ci/github/ui-quality-gate.yml
```

The two pipelines run independently and only when their respective tree changed.

**Option B — Single composite pipeline.** Copy the relevant jobs from each shape's CI file into a single workflow with `if:` conditions that check the affected paths. More work to wire up but lets you share infrastructure (e.g., a common `setup` job).

The `repo-scope-check.yml` gate (multi-repo scope validation) lives under each app's `ci/<provider>/` — it's identical content, so you can install it once at the repo root and delete the per-app copies if preferred.

---

## Feature governance in a monorepo

`features/` directories are **per-app**, not monorepo-wide:

- A backend feature lives at `apps/api/features/<feature_name>/`
- A UI feature lives at `apps/web/features/<feature_name>/`

This is intentional: a feature owned by the backend team has its own NFRs, evaluation criteria, and architecture preflight — none of which are appropriate for a UI-team feature, and vice versa.

If a feature genuinely spans both apps (e.g., a new endpoint AND its consuming UI), document the cross-app coordination in the **primary owner's** `nfrs.md` "Repository Scope" section. Treat it the same way you'd treat a cross-repo feature (see [CROSS_REPO_FEATURES.md](docs/CROSS_REPO_FEATURES.md)) — the only difference is the second "repo" is `apps/web/` instead of a separate git repository.

---

## Upgrading a monorepo

`govkit upgrade` operates on `--target`, so run it once per app:

```bash
pip install --upgrade govkit
govkit upgrade --target apps/api
govkit upgrade --target apps/web
```

Each upgrade independently refreshes its own `docs/`, `governance/`, and CI files without touching the sibling app.

---

## Gotchas

1. **Don't run `govkit apply` at the repo root** if you also have `apps/<shape>/` installs — the root install will create top-level `features/`, `docs/`, `.claude/`, etc. that conflict with the per-app installs. If you accidentally do this, delete the root-level govkit artifacts and re-apply per app.

2. **Don't share `governance/` across apps.** Each shape has different evaluation criteria (backend: FIRST + 7 Virtues + LLM evals; UI: FIRST + accessibility + Playwright coverage). Keep them separate.

3. **Watch for `applyTo:` over-reach on Copilot.** Without the monorepo-prefix adjustment described above, UI instructions may accidentally apply to backend code paths and vice versa. Spot-check by opening a file in each tree and verifying Copilot only surfaces appropriate rules.

4. **The `--ci` selector applies per-app.** A monorepo running both GitHub Actions and Azure DevOps would be unusual; if you do mix CI providers between apps, set `--ci github` for one and `--ci azure` for the other and the appropriate gates will install in each.

---

## Comparison: monorepo vs separate repos

| Concern | Monorepo (this pattern) | Separate repos |
|---|---|---|
| Shared types / contracts | Easy — import from `packages/shared/` | Hard — publish a versioned shared package |
| CI coordination | Path-filtered workflows in one repo | Separate CI per repo |
| Cross-app feature changes | Single PR can touch both | Multi-repo coordination (see CROSS_REPO_FEATURES.md) |
| Team independence | Shared git history | Each team owns their repo |
| govkit configuration | Per-app via `--target apps/<shape>` | Per-repo, separate `.govkit` markers |

govkit doesn't prefer one over the other — both patterns work. Pick based on your team's git strategy.
