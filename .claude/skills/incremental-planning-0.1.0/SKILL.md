---
name: incremental-planning
description: Plan implementation work as a sequence of the smallest independently demonstrable increments. Use when given a feature request, a body of work, or any implementation task that must be broken down or sequenced BEFORE coding — it classifies the request, identifies the next demonstrable behaviors, and recommends (advisory) an appropriate model tier for implementing each increment. This skill plans; it does not write code, tests, commits, or architecture.
---

# Incremental Planning

## Purpose

Plan implementation work as a sequence of the smallest independently
demonstrable increments.

This skill **does not write code**. Its responsibility is to determine the next
demonstrations that should exist, not how they should be implemented.
Implementation, testing, refactoring, commits, pull requests, and releases are
responsibilities of other skills.

## Core Principle

Grow system capability by admitting one new coherent behavior at a time.

Each proposed increment should expand the system's capabilities in exactly one
coherent way while leaving the system in a deployable, demonstrable, and
coherent state.

## Planning Algorithm

Given any implementation request:

1. Classify the request.
2. Determine whether it already represents a demonstrable increment.
3. If not, discover the smallest sequence of demonstrable increments.
4. Validate each proposed increment.
5. Stop.

Do not produce implementation guidance. Do not generate code.

## Request Classification

- **Ready Increment** — already the smallest independently demonstrable
  increment. → Implement as a single increment.
- **Composite Increment** — contains multiple independently demonstrable
  increments. → Split into the smallest sequence of independently demonstrable
  increments.
- **Hidden Increment** — phrased in implementation terms but implies one or more
  demonstrable behaviors (e.g. "Implement UploadService", "Build Search API",
  "Add CSV Import"). → Recover the demonstrations hidden within the request; do
  not preserve implementation-oriented wording if demonstrable behavior can be
  identified.
- **Technical Work** — intentionally performs engineering work rather than
  expanding externally observable capability (e.g. "Refactor duplicated code",
  "Upgrade framework version", "Rename public types", "Improve performance").
  Do not force into stories. If it supports a future demonstrable increment,
  mention that relationship without expanding scope; otherwise recommend
  implementing it directly.
- **Indeterminate** — cannot responsibly determine demonstrable behavior. State
  why. Do not invent requirements. Stop.

## Planning Heuristics

When capability is expanding, prefer progressive admission. Examples (not rules):
reject-first, validation-first, no-answer-first, quarantine-first,
empty-state-first, deny-first, stub-first. Choose the strategy that most safely
grows capability one coherent behavior at a time.

**Prerequisite-first ordering (Make the Change Easy).** An agent's default
instinct, when the cleanest implementation of an increment is blocked by a gap
in a *different*, already-existing feature (e.g. it is single-language,
single-backend, or otherwise hardcoded to one case where this increment needs
several), is to route around that gap — special-casing or duplicating logic
beside it rather than through it. Do not take that instinct for granted. Before
sequencing the increment, compare: (a) implement it around the gap, versus (b)
generalize the constraining feature first, then implement the increment as a
simple extension of it. This is Kent Beck's *Tidy First?* rule applied across
feature boundaries: "make the change easy, then make the easy change." If (b)
is no larger than (a) and produces a simpler, more coherent result, sequence
the generalization as its own earlier increment (or as this increment's
Supporting Technical Work) instead of encoding a workaround — don't default to
the workaround just because it avoids touching other code. Do not over-build
the prerequisite beyond what this increment actually needs. (Apply
`zom-representation`'s Zero-One-Many test to the constraining feature to judge
whether it can absorb the new case naturally.) Before treating the
prerequisite as newly discovered scope, check whether the project already
tracks it (a backlog doc, issue tracker, or todo list); if so, don't re-derive
or duplicate it as fresh Supporting Technical Work — recommend reordering:
promote that existing item ahead of the current increment and cite it, rather
than inventing competing scope.

## Model Recommendation (advisory)

For each increment, recommend the model best suited to *implementing* it, so the
coding step runs on an appropriately-powered model. This is a routing hint, not
implementation guidance — the executing agent or developer confirms it and
switches (via `/model` or the `model` setting) before coding. Planning still
stops at the plan; it does not code.

Judge from two inputs together:

**1. Tool evidence** for the files the increment will most likely touch, from
whatever deterministic analysis tooling the project has — history tooling
(churn/hotspots, co-change/affinity, bridge files, commit-type mix) and
current-state tooling (identifier usage breadth, import/dependency graphs,
recurring literal values) are two distinct, complementary categories; use both
where available (e.g. terrier for current-state, scenter for history, or
whatever a project provides — check for an `--agent-usage`-style
self-description or equivalent docs). Read:

- *a bridge file, high co-change coupling, or a dense cluster* (history) →
  design-bearing; a boundary or shared concept is in play.
- *high churn* (history) → the file carries a lot of future change, so getting
  the representation right matters more.
- *a long `fix` streak* (history, commit-type mix) → instability; the design
  keeps attracting bugs and needs care.
- *wide domain footprint, recurring magic values, or dense imports*
  (current-state) → a shared concept or coupling already present in the code.

When the target files are new, the project has no such tooling, or the repo is
too small/flat for meaningful signal, fall back to complexity alone.

**2. Increment complexity** — scope, ambiguity, cross-module reach, whether a new
abstraction is introduced, and how much judgment the change requires.

Map the combined read to a tier (names are model *families*, not fixed IDs; use
the project's available models):

- **Opus (heaviest)** — design-bearing or ambiguous: touches a
  bridge/dense-cluster/high-churn file, introduces or reshapes an abstraction,
  spans modules, or resolves a `fix` streak. Judgment-heavy work.
- **Sonnet (mid)** — a clear, localized change with moderate signal: well-scoped
  but with real design choices to make.
- **Haiku (lightest)** — mechanical and well-specified in a quiet, low-coupling
  file: an extract-with-existing-tests, a rename, a doc or config edit.

State the recommendation with a one-line rationale citing the signal that drove
it (e.g. "Opus — target is a bridge file with churn 20; a boundary change").

## Validation

Every proposed increment should satisfy all of the following:

- **Demonstration** — Can an interested stakeholder observe that this capability
  now exists? If not, keep refining.
- **Coherence** — Does it introduce exactly one coherent behavior? Evidence of
  that behavior (status codes, messages, logs, events, metrics, UI updates,
  database changes, etc.) belongs to the same increment. Do not split evidence;
  split behaviors.
- **Deployment** — Could it be deployed independently? If not, explain why.
- **Learning** — Does it provide customer value or reduce an important
  uncertainty? If neither, explain why it is still worthwhile.
- **Survivability** — If development stopped permanently after this increment,
  would the system remain coherent? It need not be complete, but it must remain
  internally consistent and potentially releasable.

## Output Format

Return:

**Classification** — one of: Ready Increment, Composite Increment, Hidden
Increment, Technical Work, Indeterminate.

**Assessment** — a brief explanation.

**Recommended Demonstrable Increments** — if decomposition is appropriate,
provide for each increment:

- **Title**
- **Demonstration** — What would someone do, observe, or experience that proves
  this increment exists?
- **Purpose** — Customer value or learning objective.
- **Supporting Technical Work** — Only the engineering work necessary to realize
  this demonstration. Do not describe implementation, architecture, commits, or
  development practices. Describe only the evolution of observable system
  capability.
- **Recommended Model** — the tier from *Model Recommendation* (advisory), with a
  one-line rationale citing the evidence signal and/or complexity that drove it.

**If no decomposition is recommended**, state why (e.g. already the smallest
demonstrable increment; legitimate technical work; cannot responsibly infer
demonstrable behavior) — and still give a **Recommended Model** for carrying out
the single increment.

## Guiding Philosophy

The planner optimizes for demonstrations, not implementation. Engineering may
implement an increment using many small commits; product may demonstrate or
release any completed increment. Those decisions belong to implementation and
business planning. This planner's responsibility ends when the next coherent
demonstrations have been identified — helping teams and coding agents evolve
systems safely by growing capability one coherent behavior at a time.
