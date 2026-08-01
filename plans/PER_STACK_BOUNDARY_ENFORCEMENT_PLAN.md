# Per-Stack Boundary Enforcement Plan

**Status:** In progress — 2026-08-01. Increments 1-4 are done: stack-selected
dispatch (#102), stack-agnostic doc wording (#103), Node (#105), and Go. Three
of five stacks now have boundary enforcement in a tool that can read them.
Remaining: increment 5 (JVM) and 6 (.NET), both template-and-structural-
assertion shaped. Covers #93, which closes when increment 6 lands.

Every linter adopted so far reports success on an empty analysis, each in its
own way, and none of them says so. That pattern is now the first thing to test
for when adding a stack — see Verification.

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

### 3. Node — dependency-cruiser — done

Landed via #105. `tests/test_dependency_cruiser_reference.py` runs the real
linter: conforming flat and `src/<package>/` skeletons pass, eleven forbidden
edges are each rejected, and cross-service independence is checked.

Three things the tool decided for us, none of which were guessable:

- Layer paths ship as **arrays of two regexes**. dependency-cruiser rejects
  `^src/(?:[^/]+/)?api/` as ReDoS-unsafe and bails out entirely. The pair also
  lets one config serve both layouts the payload describes.
- The **independence rule ships enabled**, unlike import-linter's. Its pattern
  requires a `src/<service>/<layer>/` segment, so it is inert on a flat
  single-service repo.
- The reference is **`.cjs`**, the filename `TECH_STACK.md:186` already names.

`by_stack` had to carry the **reference contract as well as the gate**. A real
`govkit apply` caught what the manifest tests could not: a Node install got
`boundary-gate-node.yml`, whose notice names a `.cjs`, alongside
`importlinter-reference.toml` and no `.cjs` at all. Fixing that also stopped
shipping the Python contract to the stacks whose linters cannot read it.

Commit: `feat(ci): boundary enforcement for nodejs-fastify (#93)`

### 4. Go — go-arch-lint — done

Same shape, with `actions/setup-go`. `tests/test_go_arch_lint_reference.py`
runs the real linter against generated skeletons.

Two Go-specific facts changed the design:

- **go-arch-lint exits 0 on source it cannot parse**, reporting
  "OK - No warnings found". A syntax error anywhere turns the gate green, so
  the gate runs `go build ./...` first and the fixtures assert they compile.
- **Go itself forbids import cycles.** In a fully-wired conforming skeleton,
  `adapters` imports `services`, so adding `services -> adapters` produces a
  project that does not build — and per the above, go-arch-lint would then
  pass it. Each forbidden edge is tested against a *minimal* skeleton holding
  only that edge, so the linter is what rejects it rather than the compiler.

Two config constraints worth recording, both discovered by running it:

- `common: mayDependOn: []` is **rejected** ("should have ref in
  'mayDependOn'/'canUse' or at least one flag"). Dependency-free is expressed
  by omitting the component from `deps` entirely — which reads like an
  oversight, so a test asserts the omission is deliberate.
- A component whose folder does not exist is a **hard error**, so the
  reference cannot pre-declare an `app` component for teams whose composition
  root is `internal/app/`. It documents how to add one instead. Conversely, a
  package under `internal/` that no component claims fails the check — the one
  place these linters refuse to ignore code silently.

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
- **Find the silent-pass mode before shipping the gate.** Every boundary
  linter adopted so far reports success on an empty analysis, and none
  announces it. Each was found by running the tool, never by reading its
  docs:

  | Tool | Passes vacuously when | Gate closes it with |
  | --- | --- | --- |
  | import-linter | `root_package` names a directory, not a package — 0 dependencies, all contracts KEPT | adopters told to check the analysed count |
  | dependency-cruiser | `--output-type json` (always exits 0); TypeScript 7 installed (0 modules) | default reporter + fail on zero modules |
  | go-arch-lint | source does not parse — "OK - No warnings found" | `go build ./...` first + fail on zero mapped files |

  Assume the next one has such a mode and go looking for it. A gate that
  cannot fail is worse than no gate, because it reports that the boundary
  holds.
- **Verify the reference contract installs, not just the gate.** The Node
  gate shipped without its `.cjs` and every manifest-level test was green;
  only a real `govkit apply` showed the gate pointing at a file that was not
  there.

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
  (`:49-54`), and secrets via Pydantic's `BaseSettings` (`:81`). A `go-gin`
  install reads all of that, and §10 tells agents to cite this contract when
  generating code. Filed as **#104**.

- **Retiring superseded gate files on upgrade.** Increment 1 moves
  `boundary-check` out of `l3-quality-gate.yml`; an existing install keeps
  the old file until upgrade refreshes it. Verified by hand against a
  simulated pre-change install: `upgrade` rewrote `l3-quality-gate.yml` and
  added `boundary-gate-python.yml`, so the job is never defined twice. The
  behaviour is correct; what is still missing is an automated test pinning
  it — related to #83.
