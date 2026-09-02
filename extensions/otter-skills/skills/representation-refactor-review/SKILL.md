---
name: representation-refactor-review
description: Review code and propose evidence-based representation improvements using Tim Ottinger's Eight Code Virtues, SPOT, ZOM, and the improvement test. Use for broad craft, refactoring-readiness, clean-code, knowledge-representation critique, or discovering data clusters, data classes, and class-splitting boundaries. Do not use for bug/security-only review, implementing behavior test-first, or a focused identifier-naming task; those belong to the relevant specialist workflow.
---

# Ottinger-Style Code Review: Representation & Refactor

This skill drives **concrete refactoring suggestions** — rename, extract, introduce type, replace conditional with table — grounded in Tim Ottinger's Eight Code Virtues and knowledge-representation lens. It is not an approval checklist or a style-only pass. Every finding must identify a representation problem and end in a specific mechanical move. If the evidence supports no objections, say so plainly.

The deliverable is a **prioritized list of representation concerns and refactor recommendations**. Each item names the virtue(s) under pressure, shows the evidence, and prescribes the smallest change that improves the knowledge representation across multiple virtues together. Apply the ideas; do not impersonate Ottinger or claim he personally reviewed the code.

## When this skill owns the task

Use this skill for a broad review of how code represents domain knowledge, or when the user explicitly invokes the Eight Virtues, SPOT, ZOM, Coherent, the improvement test, or Ottinger-style review.

Do not use it as the primary skill for:

- correctness-, bug-, performance-, or security-only review without a requested representation lens
- implementing new behavior or a bug fix test-first; use `unit-testing`
- establishing test access and characterizing poorly understood existing behavior; use `legacy-code-safety`
- choosing or sequencing delivery slices; use `story-splitting-for-delivery`
- a focused request to choose, diagnose, or rename identifiers; use `code-object-naming`

A broad representation review may still surface naming and test-design evidence. Keep the broad review here and use the sibling's specialized guidance only for the deeper sub-pass.

## Progressive disclosure

| Load | When |
| --- | --- |
| This file | Always when the skill is active |
| [`references/virtues.md`](references/virtues.md) | Before writing findings — definitions, improvement test, Coherent, comments |
| [`references/class-boundaries.md`](references/class-boundaries.md) | When data clusters, construction semantics, extracting a class/value object, or splitting a class are in scope |

Keep the workflow here; put depth in the reference. Use the sibling `code-object-naming` skill when a review needs a dedicated naming pass.

## Mindset

Internalize these before reading a line:

- **Code is written for an audience, most of whom are not the author.** Readability is a relationship between code and its maintainers—not author satisfaction.
- **Good software is primarily a good representation of knowledge.** Working is table stakes. Prefer changes that give knowledge a clearer, more unique, simpler, more developed, briefer, more coherent home.
- **Naming is among the most powerful tools available.** Difficulty naming is diagnostic; structure is often not crisp yet.
- **Distinguish objective virtues from subjective ones.** Working, Unique, Simple, Developed, Brief, and Coherent can be evidenced. Clear and Easy are subjective relationships. Name which kind each finding is.
- **Working is prime; the other seven virtues are peers in balance.** Do not apply a fixed ladder (Unique > Simple > …). Prefer multi-virtue representation wins. Use the **improvement test** for tradeoffs.
- **Observation ≠ prescription.** Pressure on a virtue does not dictate the refactoring. Separate observation, inference, and action.
- **A struggle to read code should be profitable, not needless.** Attack needless difficulty; respect difficulty that teaches the domain.
- **Refactoring is the path, not the verdict.** Every objection should imply a concrete mechanical move (extract, rename, introduce type, replace conditional with table, etc.).
- **Be relentless but not cruel.** Attack the artifact; respect the human.

## Workflow

1. **Establish Working first.** Inspect the project instructions and diff before choosing checks. Run the narrowest relevant existing tests when the user has asked for a review and local, non-mutating verification is available. If you cannot verify behaviour, state that limitation. Missing tests is a finding only when it creates a concrete regression risk for changed behaviour; absence alone is not automatically P1.
2. **Read for the audience.** Flag every place you reverse-engineered intent.
3. **Pass systematically against the Eight Virtues and naming.** Read [`references/virtues.md`](references/virtues.md). Use `code-object-naming` for a naming-heavy sub-pass. Go virtue by virtue (Working, then the seven peers), including boundaries and dependencies when they are in scope. Do not pattern-match a few smells and stop. **Within the Unique, Developed, and Coherent passes, run the ZOM Drift sub-pass (see below).**
4. **For every concern capture:** (a) location, (b) virtue(s) under pressure, (c) concrete refactoring, (d) *why it matters* to audience/maintenance. No "why" → drop it.
5. **Prioritize and assemble** the final report in the format below.

## ZOM Drift Pass (Unique · Developed · Coherent)

Run this pass while evaluating **Unique**, **Developed**, and **Coherent**. ZOM (Zero-One-Many) drift occurs when a representation fails to evolve as the codebase changes—staying at One when Many cases exist, staying scattered when a concept needs a single owner, or remaining when the concept is gone.

**Always report evidence first. Infer second. Never lead with the redesign.**

### Step 1 — Collect evidence

Scan for these markers:

- Repeated name stems (`name1`/`name2`, `primaryX`/`secondaryX`)
- Repeated constants or enum values handled across multiple sites
- Repeated parameter groups passed together in multiple call sites
- Variables consistently manipulated together (traveling values)
- Methods that all operate on the same data
- Long conditional chains or large switch statements
- Many boolean flags controlling unrelated variation
- Duplicate private helpers or validation/parsing logic scattered across files
- Tests that repeat the same setup for the same concept

### Step 2 — Classify the ZOM state

| State | Signal | Virtues under pressure |
| --- | --- | --- |
| **Zero pretending to be One** | Dead branches, obsolete parameters, unused abstractions, configuration for removed behaviour | Unique (false SPOT), Coherent (ghost dialect) |
| **One pretending to be Many** | Numbered twins (`item1`/`item2`), parallel helpers, repeated parameter groups | Unique (latent duplication), Developed (missing collection or value object) |
| **Many pretending to be One** | Long conditionals, large switch, flag piles, one class handling unrelated cases | Simple (path count), Developed (missing variation representation), Coherent (implicit dialect) |
| **Many without Ownership** | Duplicate helpers, domain logic in utilities, same enum handled in many modules | Unique (SPOT violation), Coherent (scattered authoritative truth) |

### Step 3 — Ask what multiplied

When Many evidence appears, ask what the Many really is:

- Values → collection
- Parameter/field groups → value object
- Behaviour on the same data → owning type
- Same role in different places → strategy or table
- States → state model
- Rules → policy object or table
- Scattered owners → one authoritative home

### Step 4 — Produce ZOM findings

For each concept identified, capture:

```text
Concept:
Evidence (observations):
Current representation:
ZOM state (inference):
Virtues under pressure:
Smallest suggested representation improvement:
```

Integrate these findings into the main report at the appropriate P-level. ZOM-without-ownership and One-pretending-to-be-Many findings on shared facts are typically P1–P2 (Unique). Missing-type findings are typically P2–P3 (Developed). Dead representation is typically P2 unless it actively misleads (then P1 for Coherent/Unique).

## Minimum evidence for class recommendations

Clumping suggests a boundary; a meaningful name and independent rules confirm it. Do not recommend a class or split from size, field count, method count, or clumping alone.

- **Introduce a class:** values repeatedly travel together **and** share construction rules, invariants, normalization, or behaviour worth owning.
- **Split a class:** methods and fields form at least two distinct clusters; each cluster names a meaningful concept; and their necessary interaction fits through a small interface.

When either recommendation is plausible, read [`references/class-boundaries.md`](references/class-boundaries.md) before reporting or changing code. Record evidence against the recommendation as well as evidence for it.

## How to be exacting

- **Go function by function, name by name.** Enumerate; do not only generalize. Group related names if needed, but account for all of them.
- **Tie every objection to a principle.** "I don't like this" is not a finding. SPOT, path count, primitive cluster, dialect clash, ZOM state, etc. are findings.
- **Prefer evidence where it exists.** Count ops/operands/paths; point at knowledge homes; show competing representations for Coherent; show co-change for Easy/Unique; enumerate stems for ZOM.
- **Do not use a fixed peer-virtue ordering to win tradeoffs.** Working always wins. Among peers, argue the multi-virtue outcome and the real change being made.
- **Name the refactoring, not just the smell.** End in a verb: *extract*, *rename*, *introduce*, *replace*, *inline*, *split*, *gather*, *invert*, *derive*.

## Standing refactoring instruction: knowledge representation first

Use when the task includes code changes, not only review comments.

Act as if good software is primarily a good representation of knowledge. Passing tests is necessary, not sufficient. Refactor so the representation is more Unique, Simple, Clear, Easy, Developed, Brief, and Coherent while preserving behaviour.

### Core rule

- Do not refactor for style alone.
- Refactor when evidence shows knowledge is poorly represented, duplicated, scattered, too primitive, dialect-split, or no longer matches what the code now reveals.

### Method

Before changing code, inspect nearby implementation and tests. Look for:

- repeated names or stems
- repeated parameter/field groups
- values manipulated together
- methods on the same data
- duplicated helpers/policies/constants
- growing conditionals/switches
- enums/constants handled in many places
- competing representations of one concept (Coherent pressure)
- tests with the same setup repeatedly
- functions/files that change together

When you find these markers, apply the ZOM Drift Pass (above) before proposing any change.

### Improvement test (required)

Keep a change only if:

1. Working is preserved (tests/evidence), and
2. the overall representation is better across the peer virtues **together**.

If not better overall, revert or choose a smaller experiment.

### Working procedure

1. State the concept under review.
2. List concrete evidence (observations).
3. Describe current representation.
4. Identify ZOM / repetition / dialect signals (inferences).
5. Propose the smallest representation improvement.
6. Make the change.
7. Preserve or add tests; run them.
8. Re-evaluate with the improvement test.
9. Revert or shrink if the result is not better.

### Constraints

- No speculative abstractions or named patterns without evidence.
- Not "fewer lines alone," not "smaller files alone."
- No behaviour change unless requested.
- Always separate observations, inferences, and actions.

### Required refactoring output

Before changes:

```text
Concept:
Evidence (observations):
Current representation:
ZOM/repetition/coherence signal (inference):
Proposed representation improvement:
Virtues under pressure / expected multi-virtue gain:
Tradeoffs to watch:
```

After changes:

```text
Behaviour preserved:
Tests:
Representation improvement:
Improvement test (Working + peers together):
Tradeoffs:
Remaining concerns:
```

## Priority indicators

Assign exactly one per finding:

- **P1 — Critical.** Threatens **Working** or **Unique** in a way that can corrupt behaviour or silently break under maintenance: demonstrated bugs, failing relevant tests, a concrete untested regression path in changed code, duplicated facts/algorithms (SPOT), competing executable truths, shared mutable assumptions. ZOM findings that create silent divergence of shared facts belong here.
- **P2 — Major.** Serious pressure on **Simple**, **Clear**, **Developed**, or **Coherent** that will measurably slow or mislead maintainers: high path complexity, primitive obsession, disinformative/unsearchable names, not-logic, abstraction leaks, conflicting dialects for the same concept, pattern thrash. ZOM findings of One-pretending-to-be-Many and Many-without-Ownership belong here when they affect co-change.
- **P3 — Minor.** Pressure on **Easy**, **Brief**, or milder Coherent/Developed issues: awkward-to-change structure for likely changes, missing helpful abstractions, chatty code, mild inconsistency, mild idiom drift. Zero-pretending-to-be-One (dead code) typically lands here unless it actively misleads.
- **P4 — Polish.** Subjective preferences and team-negotiable conventions within an acceptable band. Flag as subjective; never inflate.

Optional band markers when the medium renders them well: 🔴 P1 · 🟠 P2 · 🟡 P3 · 🔵 P4.

Within a band, order by impact. Prefer multi-virtue representation fixes higher when severity is similar.

## Review output

Follow Codex's findings-first review convention. Present findings in descending severity, then unresolved assumptions or verification gaps, and finish with a short verdict. If there are no findings, say so directly and mention residual testing risk. Do not emit empty priority sections.

Use this shape for each finding:

```markdown
### [P1–P4] [Imperative or concrete title]

- **Location:** `[file:line]`
- **Virtues under pressure:** [list]
- **Observation:** [what the code demonstrates]
- **Inference:** [why that evidence indicates a representation problem]
- **Action:** [specific refactoring move]
- **Why necessary:** [maintenance or behavioural consequence]
```

Report rules:

- Make locations precise and use clickable local file links when Codex can provide them.
- Every objection needs all six fields; **Why necessary** is non-negotiable.
- Findings must be countable and auditable.
- Do not pad P4 or starve P1.
- Keep praise brief and only mention qualities that materially constrain a proposed change.
- When several findings share one representation cause, group them if one fix resolves them; preserve distinct locations as evidence.

## Codex operating notes

- Read repository instructions such as `AGENTS.md` and preserve the user's unrelated work.
- Prefer project scripts (`./run_tests`, `./tidy`, `./prepare`) when present.
- Do not modify existing tests to bless broken behaviour without explicit user permission.
- A review request authorizes inspection and non-mutating checks, not implementation. Only edit code when the user asks for fixes.
- Do not create commits unless the user asks. When implementing fixes, keep structural and behavioural changes separable in the diff.
- Load only the reference files needed for the current pass.

## Related skills

- `legacy-code-safety` owns characterization, seams, and dependency breaking needed before risky legacy changes. This skill may identify the risk but does not establish the safety boundary during a review.
- `code-object-naming` owns focused identifier choice, diagnosis, and rename planning. This skill may identify naming as evidence inside a broader representation review.
- `unit-testing` owns test-first implementation and focused FIRST/flakiness work. This skill may review test code as part of a broader representation critique, but does not replace the TDD loop.
- `story-splitting-for-delivery` owns the choice and sequence of delivery slices; representation review does not turn design concerns into a backlog plan.

## Diligence statement

If the user asks for an AI-use disclosure in a saved review, adapt the template in `AI_DILIGENCE.md`. Do not add disclosure files to reviewed projects without that request.
