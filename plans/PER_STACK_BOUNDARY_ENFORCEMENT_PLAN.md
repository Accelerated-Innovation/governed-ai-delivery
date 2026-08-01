# Per-Stack Boundary Enforcement Plan

**Status:** In progress — 2026-08-01. Increment 1 (stack-selected dispatch,
proven with Python) landed via #102. Increment 6 (documentation) was pulled
ahead of 2-5 and is landing now — its wording fix is correct regardless of
which tools follow. Increments 2-5 are unblocked: open questions 1-3 are
answered below, and 4 is scoped to a per-stack check rather than a blocker.
Covers #93, which closes when increment 5 lands.

Decisions taken 2026-08-01, after the open questions were revisited against
the shipped payload:

- **Tool choices were never open.** Each stack overlay already names its tool.
  See the corrected table in Motivation §3.
- **All five stacks stay in #93.** The overlays already promise ArchUnit and
  ArchUnitNET to java-spring-boot and dotnet-aspnet users, so dropping those
  two would leave a documented promise unmet with no issue tracking it.
- **Node and Go get real fixture tests**, with Node and Go toolchains added to
  CI. Java and .NET get structural assertions only, stated plainly rather than
  implied.
- **Baseline docs stay stack-agnostic** rather than joining the overlay set.

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

Worse, it contradicts docs in the *same install*. Only six architecture docs
are overlaid per stack, and three of them already name the right tool. A
`go-gin` L4 install read this, verified against a real `govkit apply`:

| Doc | Source | Says |
| --- | --- | --- |
| `TECH_STACK.md` | overlay | `go-arch-lint` |
| `LAYER_IMPLEMENTATION.md` | overlay | "Enforced via **`go-arch-lint`**" |
| `TESTING.md` | overlay | "verified by `go-arch-lint`" |
| `BOUNDARIES.md` | **baseline** | "All are enforced with `import-linter`" |
| `ARCH_CONTRACT.md` | **baseline** | "Enforced via `import-linter` and PR review" |

`BOUNDARIES.md` and `ARCH_CONTRACT.md` are not in any overlay's `docs` list,
so they ship byte-identical to all five stacks. That is the right call — the
layer rules genuinely are stack-agnostic — but it means they must defer to
`TECH_STACK.md` on the tool rather than naming one.

The CI gates are stack-agnostic too: no `cli/stacks/*/overlay.yaml` varies
them, so every backend install receives the same Python job.

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

**The tools are already chosen.** Every stack overlay names its boundary
tool today. This plan implements what the payload already promises rather
than picking anew:

| Stack | Tool | Already named at | Shape |
| --- | --- | --- | --- |
| python-fastapi | import-linter | `TECH_STACK.md:173`, `LAYER_IMPLEMENTATION.md:383` | config (`pyproject.toml`) + CLI |
| nodejs-fastify | dependency-cruiser | `TECH_STACK.md:176`, `LAYER_IMPLEMENTATION.md:301` | config (`.dependency-cruiser.cjs`) + CLI |
| go-gin | go-arch-lint | `TECH_STACK.md:172`, `LAYER_IMPLEMENTATION.md:318` | config (`.go-arch-lint.yml`) + CLI |
| java-spring-boot | ArchUnit | `TECH_STACK.md:174`, `LAYER_IMPLEMENTATION.md:299` | **test code** — rules are JUnit test classes |
| dotnet-aspnet | ArchUnitNET | `TECH_STACK.md:176`, `LAYER_IMPLEMENTATION.md:337` | **test code** — rules are xUnit/NUnit tests |

(Paths are relative to `cli/stacks/<id>/`.)

For the first three, govkit ships a reference *config* the team copies, and
CI runs a linter — the `importlinter-reference.toml` pattern. The Node
reference file is `.cjs`, not `.js`: `nodejs-fastify`'s `TECH_STACK.md:186`
already tells teams the file is `.dependency-cruiser.cjs`, and the shipped
reference should match the name the docs promise.

For Java and .NET there is no config file. The rules are written as tests in
the project's own suite, so govkit ships a **template test class** and CI
simply runs the existing test command. Different artifact, different
install location, different verification story.

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

### 2. Stack-agnostic docs stop naming a stack's tool — done

Pulled ahead of the tooling increments: the wording fix is correct whichever
tools follow, and it closes the window where four stacks have no gate *and*
baseline docs still promise `import-linter`.

1. Failing test in `tests/test_layer_vocabulary.py`: no backend architecture
   doc that a stack overlay does *not* replace may name a boundary tool. The
   scanned set is derived from the overlays' own `docs` lists rather than
   hardcoded, so it stays correct if the overlay set changes, and the test
   asserts `BOUNDARIES.md` and `ARCH_CONTRACT.md` are actually in that set
   so it cannot pass vacuously.
2. `BOUNDARIES.md:48` and `ARCH_CONTRACT.md:43,106` defer to `TECH_STACK.md`
   for the tool. Three lines, two files — the docs that name tools are
   already overlaid and already correct.

Deliberately *not* promoted to the overlay set. Duplicating both docs across
five stacks to vary one sentence would recreate exactly the drift #77 existed
to close, and the layer rules themselves are identical for every stack.

`ci/README.md` was already corrected in increment 1, which moved the gate.

Commit: `docs(backend): defer to TECH_STACK.md for the boundary tool (#93)`

### 3. Node — dependency-cruiser

1. Failing fixture test, `e2e`-marked, modelled on
   `tests/test_importlinter_reference.py`: a conforming `src/<pkg>/` skeleton
   passes; each forbidden edge is rejected; **assert a non-zero module count**
   so a config that analyses nothing cannot read as passing.
2. `governance/backend/dependency-cruiser-reference.cjs`, the gate file, the
   manifest wiring.
3. `actions/setup-node` in the pytest job, **plus a CI-only assertion that
   the binary resolves**. The existing `shutil.which` skipif is right for
   local runs, but in CI a skip and a pass look identical — a broken setup
   step must fail loudly rather than quietly skip the only test that proves
   the config works.

Commit: `feat(ci): boundary enforcement for nodejs-fastify (#93)`

### 4. Go — go-arch-lint

Same shape as increment 3, with `actions/setup-go`.

Commit: `feat(ci): boundary enforcement for go-gin (#93)`

### 5. JVM — ArchUnit template

1. Failing structural test: the template names all six layers, expresses
   `api → services` as forbidden, and its layer order matches
   `BOUNDARIES.md`.
2. `governance/backend/ArchitectureTest.java.template`, gate file, wiring.
3. The gate runs the project's existing test command — it does not install
   a separate linter.

Structural assertions only — a Python test suite cannot run a JVM fixture
without a JVM in CI, which is not worth adding for a template that changes
rarely. `ci/README.md` must say so plainly rather than implying parity with
the fixture-verified stacks.

Commit: `feat(ci): boundary enforcement for java-spring-boot (#93)`

### 6. .NET — ArchUnitNET template

Same shape as increment 5. ArchUnitNET, not NetArchTest — `dotnet-aspnet`'s
overlay already names it.

Also extend `tests/test_layer_vocabulary.py` so every new contract and
template is checked against the canonical six layer names, as the
import-linter reference already is.

Commit: `feat(ci): boundary enforcement for dotnet-aspnet (#93)`

## Verification

- `./run_tests` after each increment; `./full_test` before the PR.
- `pytest -k parity` after any manifest edit — three agents, in lockstep.
- `tests/test_ci_gate_composition.py` must stay green: no job may be defined
  by two gate files that ship together.
- Regenerate smoke sandboxes for at least one backend stack per shape.
- Confirm a stack with no gate installs cleanly rather than erroring.

## Open questions — resolved 2026-08-01

1. ~~**Tool choices.**~~ **Not open, and never was.** Every stack overlay
   already names its tool in `TECH_STACK.md` and `LAYER_IMPLEMENTATION.md` —
   see the table in Motivation §3. .NET is **ArchUnitNET**, Go is
   **go-arch-lint**; this plan originally floated both as undecided while the
   shipped payload had already told users which to use. Changing either now
   would mean editing the overlays to match an implementation choice, rather
   than implementing what the docs promise. Recorded because reading the plan
   alone would have led to picking again.
2. ~~**CI toolchains.**~~ **Yes for Node and Go.** `actions/setup-node` and
   `actions/setup-go` join the pytest job so increments 3 and 4 get real
   fixture tests at the `tests/test_importlinter_reference.py` standard, with
   a CI-only assertion that the toolchain resolves. Java and .NET keep
   structural assertions — a JVM and a .NET SDK on every run is not worth it
   for two templates that change rarely.
3. ~~**Test-code templates.**~~ **`governance/backend/`, as copy-me
   templates.** No new file category. `importlinter-reference.toml` already
   works exactly this way: govkit ships it, the docs say where to copy it.
   Writing into a team's test tree would mean guessing their test root, and
   govkit does not write files the user authors.
4. **Multi-service repos** — still open, but scoped per stack rather than
   blocking. The import-linter reference expresses cross-service independence;
   whether `dependency-cruiser`, `go-arch-lint`, ArchUnit and ArchUnitNET can
   is a question for each increment to answer and record. Where a tool cannot,
   say so in its reference file rather than leaving it implied.

## Out of scope

- **ui-nextjs boundary enforcement.** It has its own boundary story — doctor
  D016 for the database rule, plus its own gate — and UI work is parked
  pending a wider review.
- **The ui-nextjs gate duplication** found while fixing #94: both its L4
  gate files define a `quality` job, and its L5 variant already drops the L3
  file, so the manifest contradicts itself. Same parked review.
- **`ARCH_CONTRACT.md` leaks Python beyond the boundary tool.** Found while
  making the boundary wording stack-neutral, and deliberately left alone —
  it is a separate defect from #93. The same stack-agnostic file also says
  the domain may depend on "standard Python and `typing`" (`:23`), that "all
  ports are pure Python interfaces (ABC or `Protocol`)" (`:30`), and lists
  approved libraries as Pydantic, FastAPI, SQLAlchemy, `httpx` and `boto3`
  (`:49-54`). A `go-gin` install reads all of that. Needs its own issue.

- **Retiring superseded gate files on upgrade.** Increment 1 moves
  `boundary-check` out of `l3-quality-gate.yml`; an existing install keeps
  the old file until upgrade refreshes it. Verified by hand against a
  simulated pre-change install: `upgrade` rewrote `l3-quality-gate.yml` and
  added `boundary-gate-python.yml`, so the job is never defined twice. The
  behaviour is correct; what is still missing is an automated test pinning
  it — related to #83.
