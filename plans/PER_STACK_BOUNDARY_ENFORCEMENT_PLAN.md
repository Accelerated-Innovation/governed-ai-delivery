# Per-Stack Boundary Enforcement Plan

**Status:** In progress — 2026-08-01. Increment 1 (stack-selected dispatch,
proven with Python) is implemented. Increments 2-5 are held pending answers to
the Open questions below; increment 6 follows them. Covers #93, which closes
when the remaining increments land.

Give each backend stack boundary enforcement in a tool that understands its
language. Four of govkit's five backend stacks currently have none: the
`boundary-check` job runs `import-linter`, which is Python-only, against
Go, C#, Java and TypeScript alike.

## Motivation (evidence)

### 1. Four stacks ship contracts nothing enforces

`docs/backend/architecture/BOUNDARIES.md` and `ARCH_CONTRACT.md` install for
every backend stack and state that the layering is "enforced with
`import-linter`". For `go-gin`, `dotnet-aspnet`, `java-spring-boot` and
`nodejs-fastify` that sentence is false — import-linter cannot read their
source at all.

The CI gates are stack-agnostic: no `cli/stacks/*/overlay.yaml` varies them,
so every backend install receives the same Python job.

Since #95 the job skips when no import-linter contract is configured, so
those four stacks now get a *silent* skip rather than a spurious failure.
That was the honest interim state, not a fix — a skipped job enforces
nothing, and the architecture docs still promise enforcement.

### 2. The dispatch machinery already exists

No schema change is needed. `cli/manifest.py` supports a `by_stack` block
nested inside a `by_type` entry, and the `data` type already uses it:

```json
"by_type": {
  "data": {
    "governed": ["ci/github/repo-scope-check.yml", "ci/github/data-common-gate.yml"],
    "by_stack": {
      "python-dbt":           { "governed": ["ci/github/dbt-gate.yml"] },
      "databricks-lakehouse": { "governed": ["ci/github/databricks-gate.yml"] }
    }
  }
}
```

A common gate for the type, plus a per-stack gate — exactly the shape the
backend types need. `api` and `cli` simply have no `by_stack` block yet.

Note `stack-overlay.schema.json` allows only `docs`, `rules`,
`skill_context` and `review_checklist`, so a stack overlay *cannot* ship a
CI file. Wiring belongs in the agent manifests, not the overlay — worth
stating because the overlay is the more intuitive place to look.

### 3. The five stacks split into two artifact shapes

This is the part that makes the work bigger than "four more config files",
and it should be settled before any increment starts.

| Stack | Tool | Shape |
| --- | --- | --- |
| python-fastapi | import-linter | config (`pyproject.toml`) + CLI |
| nodejs-fastify | dependency-cruiser | config (`.dependency-cruiser.js`) + CLI |
| go-gin | go-arch-lint | config (`.go-arch-lint.yml`) + CLI |
| java-spring-boot | ArchUnit | **test code** — rules are JUnit test classes |
| dotnet-aspnet | NetArchTest / ArchUnitNET | **test code** — rules are xUnit/NUnit tests |

For the first three, govkit ships a reference *config* the team copies, and
CI runs a linter — the `importlinter-reference.toml` pattern.

For Java and .NET there is no config file. The rules are written as tests in
the project's own suite, so govkit ships a **template test class** and CI
simply runs the existing test command. Different artifact, different
install location, different verification story.

Tool choices are proposals, not decisions — see Open questions.

Virtues: **Honest** (a gate that passes means the boundary holds),
**Coherent** (the enforcement matches the contract the docs state).

## Target design

### Dispatch

Move the Python boundary job out of the shared gates into its own
stack-selected file, then add `by_stack` blocks for `api` and `cli` in all
three agent manifests and both CI flavours:

```
ci/<flavour>/boundary-gate-python.yml     python-fastapi
ci/<flavour>/boundary-gate-node.yml       nodejs-fastify
ci/<flavour>/boundary-gate-go.yml         go-gin
ci/<flavour>/boundary-gate-jvm.yml        java-spring-boot
ci/<flavour>/boundary-gate-dotnet.yml     dotnet-aspnet
```

A stack with no boundary gate ships none, rather than one that skips. The
skip logic added in #95 stays only for the Python gate, where "contract not
yet copied in" is a real state.

### Contracts

```
governance/backend/importlinter-reference.toml        (exists)
governance/backend/dependency-cruiser-reference.js
governance/backend/go-arch-lint-reference.yml
governance/backend/ArchitectureTest.java.template
governance/backend/ArchitectureTest.cs.template
```

Every one expresses the same contract as the import-linter reference:
`api | adapters` above `services` above `ports` above `models` above
`common`, with `api → services` forbidden and cross-service independence
available for multi-service repos.

Each ships at L3 alongside `importlinter-reference.toml`, per #85 — boundary
enforcement is architectural governance, which L3 provides.

### Verification, and its limits

`tests/test_importlinter_reference.py` runs the real linter against
generated skeletons. That is the standard to match, and it is reachable for
Node and Go if CI installs those toolchains — both are cheap on
`ubuntu-latest`.

It is **not** reachable for Java or .NET in a Python test suite without a
JVM and a .NET SDK. For those two the plan proposes structural assertions
only: the template names every layer, expresses each required edge, and
stays consistent with `BOUNDARIES.md`. That is weaker, and the plan should
say so rather than imply parity.

The alternative — adding JVM and .NET toolchains to CI — is a real cost on
every run for two templates that change rarely. Recommend structural
assertions plus a documented manual check, and revisit if the templates
start drifting.

## Increments

Each is independently demonstrable and starts with failing tests. Payload
edits land for **all three agents in lockstep**; run `pytest -k parity`
before each commit.

### 1. Stack-selected dispatch, proven with Python — done

1. Failing test: a `python-fastapi` install receives a boundary gate; a
   `go-gin` install receives none. Assert per agent × CI flavour × type.
   → `tests/test_boundary_gate_dispatch.py`, which also asserts the job is
   defined in exactly one of the two files, and that UI and `data` installs
   never receive it.
2. Extract `boundary-check` from `l3-quality-gate.yml` into
   `ci/<flavour>/boundary-gate-python.yml`. (`quality-gate.yml` no longer
   defines it — #94 removed the L4 duplicate before this plan was written.)
3. Add `by_stack` blocks under `by_type.api` and `by_type.cli` in all three
   manifests, both flavours — at the base block and again under `level_5`,
   which is `replace` mode and so does not inherit the base. L4 is `merge`
   mode and inherits, as it already does for `l3-quality-gate.yml`.
4. Extend `tests/test_ci_gate_composition.py` so the no-duplicate-jobs
   invariant covers the new files — it is now parametrized over `stack`.

No new tooling — this proves the dispatch alone, and is revertible on its
own if the approach is wrong.

Verified with real `govkit apply` runs across agent × flavour × level ×
stack: `python-fastapi` receives the gate at L3/L4/L5 in both flavours,
`go-gin` and `java-spring-boot` receive no boundary workflow and install
cleanly, and `data`/`ui-nextjs` are untouched. An existing install
upgraded from a pre-change payload was also checked — `upgrade` refreshed
`l3-quality-gate.yml` (dropping `boundary-check`) and added the new file,
so no repo ends up defining the job twice. That closes the assumption
recorded under Out of scope; an automated test for it stays with #83.

Commit: `refactor(ci): select the boundary gate per stack (#93)`

### 2. Node — dependency-cruiser

1. Failing fixture test, `e2e`-marked, modelled on
   `tests/test_importlinter_reference.py`: a conforming `src/<pkg>/` skeleton
   passes; each forbidden edge is rejected; **assert a non-zero module count**
   so a config that analyses nothing cannot read as passing.
2. `governance/backend/dependency-cruiser-reference.js`, the gate file, the
   manifest wiring.

Commit: `feat(ci): boundary enforcement for nodejs-fastify (#93)`

### 3. Go — go-arch-lint

Same shape as increment 2.

Commit: `feat(ci): boundary enforcement for go-gin (#93)`

### 4. JVM — ArchUnit template

1. Failing structural test: the template names all six layers, expresses
   `api → services` as forbidden, and its layer order matches
   `BOUNDARIES.md`.
2. `governance/backend/ArchitectureTest.java.template`, gate file, wiring.
3. The gate runs the project's existing test command — it does not install
   a separate linter.

Commit: `feat(ci): boundary enforcement for java-spring-boot (#93)`

### 5. .NET — NetArchTest template

Same shape as increment 4.

Commit: `feat(ci): boundary enforcement for dotnet-aspnet (#93)`

### 6. Documentation

1. `ci/README.md`: the gate is per-stack; what each stack gets; that Java
   and .NET enforcement lives in the project's test suite.
2. `BOUNDARIES.md` / `ARCH_CONTRACT.md`: stop naming import-linter as *the*
   enforcement mechanism — name the per-stack tool, or state it neutrally.
3. Extend `tests/test_layer_vocabulary.py` so every new contract is checked
   against the canonical six layer names, as the import-linter reference
   already is.

Commit: `docs(ci): document per-stack boundary enforcement (#93)`

## Verification

- `./run_tests` after each increment; `./full_test` before the PR.
- `pytest -k parity` after any manifest edit — three agents, in lockstep.
- `tests/test_ci_gate_composition.py` must stay green: no job may be defined
  by two gate files that ship together.
- Regenerate smoke sandboxes for at least one backend stack per shape.
- Confirm a stack with no gate installs cleanly rather than erroring.

## Open questions

These want answers before increment 2, not before increment 1.

1. **Tool choices.** ArchUnit and NetArchTest are the conventional picks but
   are proposals here, not verified against the repo's constraints. .NET has
   both NetArchTest and ArchUnitNET; Go has go-arch-lint and depguard.
2. **CI toolchains.** Are Node and Go acceptable additions to the test
   matrix for fixture tests? If not, all four new stacks fall back to
   structural assertions and the verification story is uniformly weaker.
3. **Test-code templates.** Where does an `ArchitectureTest.java.template`
   install to? It is neither a governed contract nor an agent file — it is a
   file the team copies into their own test tree. That may need a new
   file category, or it may simply live in `governance/backend/` as a
   template the docs point at.
4. **Multi-service repos.** The import-linter reference expresses
   cross-service independence. Do the other four tools express it, and if
   not, is that acceptable?

## Out of scope

- **ui-nextjs boundary enforcement.** It has its own boundary story — doctor
  D016 for the database rule, plus its own gate — and UI work is parked
  pending a wider review.
- **The ui-nextjs gate duplication** found while fixing #94: both its L4
  gate files define a `quality` job, and its L5 variant already drops the L3
  file, so the manifest contradicts itself. Same parked review.
- **Retiring superseded gate files on upgrade.** Increment 1 moves
  `boundary-check` out of `l3-quality-gate.yml`; an existing install keeps
  the old file until upgrade refreshes it. Verified by hand against a
  simulated pre-change install: `upgrade` rewrote `l3-quality-gate.yml` and
  added `boundary-gate-python.yml`, so the job is never defined twice. The
  behaviour is correct; what is still missing is an automated test pinning
  it — related to #83.
