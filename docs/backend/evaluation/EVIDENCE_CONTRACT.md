# Evidence Contract

govkit requires a **planning forecast before implementation** and **measured
quality evidence before merge**. This contract defines what counts as evidence,
what a gate may conclude from it, and — honestly — which dimensions govkit can
measure today and which it cannot.

## Source

The vocabulary here is lifted from
`extensions/skill-oriented-agent-architecture/docs/backend/architecture/EVALUATION_EVIDENCE_AND_COMPLETION_CONTRACT.md`,
which govkit ships to govern the agent systems its users *build*. Promoting it
rather than inventing a parallel set of words is deliberate: two vocabularies
for the same concepts drift into meaning different things, and a framework that
holds its users to a standard its own delivery layer does not meet is not
defensible.

## Separate concepts

| Concept | Meaning |
|---|---|
| Evaluation | Measurement of a target against explicit criteria |
| Evidence | A source-linked observation record, scoped to exact versions |
| Gate decision | Deterministic application of policy to evaluated claims |
| Forecast | A prediction made before the work exists |

A forecast is not evidence. It is a planning artifact, useful for deciding
whether a plan is worth executing, and it says nothing about what was built.

## The rule this contract exists to enforce

> A **producer self-check** is advisory. The task owner **never commits its own final gate**.

A FIRST or 7-Virtue score written into `plan.md` by the agent doing the work is a
producer self-check. It is a legitimate forecast and an illegitimate gate. Any
number the producer both authors and is judged by carries no assurance, however
carefully it is cross-checked against other numbers the same producer authored.

## Gate outcomes

| Outcome | Meaning |
|---|---|
| `PASS` | Evidence exists and satisfies the criterion |
| `FAIL` | Evidence exists and does not satisfy the criterion |
| `INCONCLUSIVE` | No evidence, insufficient evidence, or evidence out of scope |
| `ERROR` | The evaluation could not be executed |

**INCONCLUSIVE is not a pass.** This is the single most important line in this
contract. An unmeasured dimension that reports green is indistinguishable from a
verified one, which is exactly how a fabricated score survives review. A gate
must report what it did not measure as loudly as what it did.

One blocking failure fails the gate. `ERROR`, missing execution, and stale
evidence never become a pass through aggregation. Weighted or averaged scoring
applies only to non-blocking criteria — which is why an *average* of twelve
dimensions cannot itself be the blocking gate.

## Evidence rules

Evidence must be:

- Produced by executing something, not by asserting something
- Source-linked — the artifact, the tool, and the run are identifiable
- Scoped to the exact commit and configuration it describes
- Independent of the producer's own claims about the work

Evidence from a different commit, configuration, or environment requires
explicit justification before it counts. Stale evidence is `INCONCLUSIVE`, not
`PASS`.

## What govkit measures today

Honest status. Most dimensions are `INCONCLUSIVE` on a fresh install, and saying
so is the point of this contract.

| Dimension | Evidence source | Status |
|---|---|---|
| Working | Test run outcome | UI only — no backend gate runs the project's tests |
| Accessibility | axe critical/serious counts | UI component tests only; the E2E axe job is a stub |
| Easy | Boundary gate (import-linter, dependency-cruiser, go-arch-lint, ArchUnit) | Where the team has adopted a boundary contract |
| Unique, Simple | SonarQube duplication and complexity | Weak — thresholds live on the Sonar server, so govkit asserts nothing about the numbers |
| Developed | Coverage | Not measured. UI uploads a `coverage/` artifact that nothing reads |
| Fast | Per-test duration | Not measured |
| Repeatable | Flake rate over repeated runs | Not measured |
| Isolated | Randomised-order and run-alone outcomes | Not measured |
| Timely | Commit ordering of test versus source | Not measured |
| Self-Verifying | Assertion shape | Not measured |
| Brief | Unused imports, commented-out code | Not measured |
| Clear | — | **Not mechanically scorable.** See below |

Every row marked "not measured" reports `INCONCLUSIVE`. None of them reports
`PASS`.

## What must never be scored mechanically

**Clear** — "identifiers are descriptive and domain-aligned", "functions do one
thing", "the code reads as prose" — is irreducibly a matter of judgement. Its
only measurable proxies (identifier length, comment density) are weak enough to
be actively misleading, rewarding verbosity over clarity.

Dimensions of this kind stay advisory. They may be scored by an **independent,
identified evaluator with evidence** — never by the agent that produced the work,
and never by a metric standing in for a judgement it cannot make.

## Forecast versus evidence

Both are required, and they answer different questions.

| | Forecast | Evidence |
|---|---|---|
| When | Before implementation | Before merge |
| Author | The planning agent | An executed tool |
| Lives in | `plan.md` `evaluation_prediction` | CI artifacts |
| Purpose | Is this plan worth executing? | Is what was built acceptable? |
| Blocking | No | Yes, where the dimension is measured |

A forecast that turns out wrong is not a governance failure — it is information.
A forecast treated as evidence is a governance failure, because it converts an
unverified claim into a green check.
