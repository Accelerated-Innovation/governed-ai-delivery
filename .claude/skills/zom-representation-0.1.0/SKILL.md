---
name: zom-representation
description: >
  Zero-One-Many Representation Evolution — use this skill whenever working with
  existing code that needs to change, grow, or be refactored. Triggers include:
  "refactor this", "add a new X to this", "this is getting messy", "how should I
  represent this", "there's a lot of duplication here", or any time numbered
  variables, growing conditionals, repeated parameter groups, or scattered
  constants are observed. Also use proactively when reviewing code for design
  quality, assessing coherence and development level, or applying the 8 Code
  Virtues framework. Do not wait to be asked — if you see representation pressure
  in the code, surface it.
---

# Zero-One-Many Representation Evolution

Your responsibility is not merely to implement the requested change.

Your responsibility is to ensure that the software's representation continues to
evolve naturally as new information is introduced.

## Operating Principle

Before writing code, determine whether the requested change can be expressed
naturally within the current representation.

If it cannot, improve the representation before extending the implementation.

Better representations often advance several virtues simultaneously. The goal is
not to maximize one virtue but to find the representation that best advances the
cluster in the area of the concept being changed.

---

## The 8 Code Virtues

"Better" means advancing toward these virtues. Working is the prerequisite — the
code must continue to work. The remaining seven are peers; none outranks another:

- **Unique**: every fact and algorithm has a single point of definition and a single point of maintenance. Duplication is eliminated — not just syntactic duplication, but duplication of knowledge.
- **Simple**: structurally fewer operations, operands, and paths at each use site. Simplicity is *local* — a call to a well-named function is simpler than the expression it replaces, even if the function's own implementation contains complexity.
- **Clear**: the code communicates intent to those who share the codebase — intent is *read*, not reconstructed by simulating the mechanics. Naming, structure, and idiom express the knowledge top-down in the language of the team and domain.
- **Easy**: the code is straightforward to change. The structure does not impose unnecessary friction when new behavior needs to be added or existing behavior modified.
- **Developed**: primitives and scattered data grow into appropriate abstractions. Things that belong together are kept together, eventually forming a domain language suited to the problem.
- **Brief**: the concept is expressed with no more syntax than it requires. Fewer total tokens to say the same thing.
- **Coherent**: concepts, abstractions, vocabulary, architecture, patterns, and representations reinforce one another. Over time, a coherent system increasingly feels like a single language — knowledge gained in one part transfers to other parts. A new type or abstraction is coherent if someone who knows the rest of the system would find it unsurprising, and if learning it helps them understand adjacent areas.

### Clarity is expression, not traceability

Primitive-oriented code — bare strings, ints, tuples, dicts, inline mechanics —
leaves *intent implicit*: the reader recovers what it means by simulating how it
runs ("playing compiler"). That step-by-step traceability is easily mistaken for
clarity, but it is bottom-up. Clarity is intent expressed *top-down in domain
vocabulary* (named types, purposeful functions) — read, not reverse-engineered.
So **primitive obsession is a clarity smell, not a clarity aid**: it optimizes
for simulatability at the expense of knowledge expression. (The
`chunk` → `commit_records` rename is the tell in miniature: a comment,
`# each chunk is one commit`, existed only to translate a primitive name into the
intent the name should have carried.)

The usual defense of primitives is debuggability — you can step through and see
everything. Weigh it against the safety net: with strong tests and diagnostics (a
TDD codebase), the value of "easy to mentally single-step" is already largely
supplied by the tests. That context shift moves the trade-off toward expression.
So when a primitive carries domain meaning — or needs an explanatory comment to
say what it *is* — prefer expressing the concept. This does **not** license
abstraction for its own sake: the candidate must still pass the Improvement Test
(evidence, not fashion). Knowledge expressed, not layers added.

---

## Activation and Calibration

Apply this rubric without being asked whenever any of the following conditions hold:

**Any code change is requested:**
Before implementing, check whether the representation should be improved first.
After implementing, check whether the change revealed new representation pressure.
Do both passes. Do not skip the after pass because the change is complete. In the
after pass, use whatever co-change/history evidence is available scoped to the
files you changed to catch historical partners the change may have left behind
(see *Gather Evidence → Evidence from the tools*).

**A test is being added:**
Tests expose the representation the code assumes. Treat a test addition as a
representation signal and apply the rubric to the code under test.

**Representation pressure signals are visible in code being read:**
Surface them. Do not wait for an explicit request.

**The request contains refactoring language** ("refactor", "clean up", "simplify",
"reorganize", "restructure", or equivalent):
The developer is explicitly requesting a change in knowledge representation and
cares about the codebase's carrying capacity — its ability to absorb future
changes without becoming brittle. Apply the full rubric. Use refactoring mode:
three highest-value, highest-confidence recommendations, ranked by evidence
strength and virtue advancement.

---

## Gather Evidence

Before making changes, examine the surrounding code.

Collect evidence from:

- names and terminology
- types
- constants and enums
- variables and fields used together
- parameter groups
- methods operating on the same data
- conditionals and switch statements
- helper functions
- validation and parsing logic
- tests
- existing abstractions
- standard library facilities

Treat these as observations. Do not draw conclusions until sufficient evidence
has been collected.

### Evidence from the tools — current-state + history

The observations above come from reading the *current* code. If the project has
deterministic analysis tooling, it adds evidence a reading pass cannot produce.
There are two distinct, complementary categories — use **both** if available:
one category says what the code *is* now, the other says how it *changes over
time*. (terrier/scenter are one such pair — a current-state tool and a history
tool — but treat any equivalent tooling the project has the same way; if a tool
self-describes its commands and blindspots, e.g. via an `--agent-usage`-style
flag or its own docs, don't hardcode its inventory here — it evolves with the
tool.)

**Current-state evidence** analyzes the code as it stands now:

- **usage breadth / footprint** — identifiers ranked by usage, split domain vs
  external. A wide *domain* footprint is a shared concept (a hidden-concept /
  value-object hint); values that co-occur across many files hint at a data
  clump.
- **import/dependency graphs** — module-dependency edges — coupling and
  dependency direction.
- **recurring literal values** — magic values in comparisons/arithmetic
  (named-constant hints).

**History evidence** reads version-control history — what neither reading nor
current-state tooling can see:

- **hotspots** (churn) — *where* representation work pays off; high-churn files
  carry the most future change.
- **affinity / clusters** (co-change) — files that change together: a concept
  spread across files, or knowledge maintained in lockstep (see the cross-file
  signals below).
- **bridges** — files connecting otherwise-separate co-change groups.
- **directions** — Conventional-Commit type mix and per-file *streaks* (softer,
  self-reported).
- **episodes** — per-file narrative (renames, thrash, maintainer handoffs).

In the **after-a-change pass**, scope co-change/affinity evidence to the files
you just touched to surface historical partners the change may have left behind
("you changed X; history says Y and Z move with it — a missed update or
duplicated maintenance?").

Treat all of it as **signals to investigate, not proof**. Co-change can be
incidental (version bumps, formatting sweeps, mass renames); confirm against the
code. The tools gather evidence; the judgment stays here.

### Mechanical checks (via the project's linter)

A linter is a deterministic evidence source too — it mechanically flags
reimplementations of language/stdlib idioms, needless complexity, and dead code
that a reading pass may miss. Gather it, preferring the project's own gate:

- **If the project has `./check` (or an equivalent quality command), run it** and
  read the findings. It reflects the project's *own* configured standards, so its
  output is the most trustworthy signal.
- **Otherwise invoke the linter directly** (e.g. `ruff check`) — it still reads
  the project's config where present.
- **If neither is available, skip this** and proceed on the other evidence. Never
  block on the absence of tooling; many target projects will have none.

Findings such as *reimplemented-operator*, *simplify*, or *perflint* hits are
direct representation-pressure signals (a hand-rolled idiom the stdlib already
owns → **Unique**, **Brief**). Treat them as signals, not orders. You are the
orchestrator of these tools; do not reimplement what they already do.

**When the linter/formatter reports something fixable, run its auto-fix mode
first.** Reach for the project's auto-fixer (`./tidy`, `ruff check --fix`,
`eslint --fix`, or equivalent) as the reflex, rather than hand-editing to
satisfy the linter or writing ad-hoc scripts to hunt for violations — auto-fix
is authoritative, faster, and less error-prone than manual reformatting.

**If an automatic formatter/linter runs between edit steps** (a save hook,
pre-commit hook, or similar), sequence multi-step changes so no intermediate
state has an unused import or symbol: introduce a declaration in the same step
as its first real usage, or land the whole unit in one shot. Otherwise the
auto-fixer can silently strip the not-yet-used symbol before its usage lands,
leaving an undefined name.

---

## Identify the Concept

Infer the domain concept affected by the change.

A concept often reveals itself through repeated observations. Evidence includes:

- common vocabulary
- repeated groups of values
- repeated behavior
- repeated ownership
- repeated variation
- repeated relationships

Determine whether the concept already has a clear owner. If it does, prefer
extending that owner.

**If the concept resists a clean name, treat that as a design signal** — not a
naming problem. A thing that cannot be named cleanly likely has multiple
responsibilities, poor cohesion, or a boundary that doesn't match a real domain
concept. Resolve the design problem first; the name will follow. (For naming
guidance once the concept is clear, apply the naming rubric separately.)

---

## Representation Pressure Signals

The following code patterns are *signals*, not mandates. Each indicates that the
representation may have fallen behind the concept it is meant to express.
Collect them as evidence before deciding anything.

### Primitives and Variables

| Observation | Representation pressure toward |
|---|---|
| A set of variables consistently appearing together (order irrelevant) | A struct, record, or value object |
| Numbered variables: `x1`, `x2`, `x3` | A list or collection (many, not multiple ones) |
| Literal strings repeated in many places | Named constants |
| Constants declared independently in multiple places | A single shared definition |
| A set of constants consistently used together | An enum that binds them |
| An `if` or `switch` that branches on constant values and dispatches different behavior | A table, map, or dictionary of records (data-driven dispatch) |
| A primitive (str/int/tuple/dict) carrying domain meaning, or one that needs a comment to say what it *is* | A named type or domain term (intent is read, not reconstructed) |

### Control Flow

| Observation | Representation pressure toward |
|---|---|
| A growing `if/else` or `switch/case` (new branch added for each new case) | A better representation of the varying dimension — polymorphism, a strategy, or a table |
| The same `if/case` pattern appearing in multiple places | A shared table, strategy, or policy object |

### Functions and Methods

| Observation | Representation pressure toward |
|---|---|
| A set of functions that consistently operate on the same data | A module (functions + data co-located) or a class (methods on the data) |
| Repeated helper functions that duplicate logic across sites | A single shared helper, possibly owned by the relevant type |
| Repeated validation or parsing logic | A method on the type being validated or parsed |
| A chain of attribute/method access reaching through another object to act on a third (`a.b().c().d()`) | Tell, Don't Ask — a delegating method on the immediate collaborator (Law of Demeter) |

### Cross-file (from change history)

These come from co-change/history evidence, not from reading a single file —
they are the *inter*-file counterpart of the signals above.

| Observation | Representation pressure toward |
|---|---|
| Two files with high commit affinity that live in separate locations | Co-locating the shared concept (a module or class the pair is really part of) |
| A cluster of files that consistently change together | A missing unit/boundary — a concept spread across files that wants one home |
| High-affinity files that change *the same way* each time | Eliminating duplicated knowledge — a single point of maintenance (**Unique**) |

### Change-direction (from commit types)

These come from commit-type-mix evidence (only where a repo uses Conventional
Commits; types are self-reported, so weigh them lightly). The thresholds —
what counts as a "long" or "recurring" streak — are your judgment.

| Observation | Representation pressure toward |
|---|---|
| A file with a long or recurring run of `fix` | Instability — a refactor candidate; the design keeps attracting bugs |
| A long run of `feat` with no `refactor`/`docs` between | Consolidation debt — clean up / extract before adding more behavior |
| A run of `test` commits | A module being brought under control — behavior is crystallizing; a good moment to support a refactor |
| Overall type mix (feat-heavy vs fix/refactor/docs mix) | A read on lifecycle phase — building vs maintaining vs decaying |

### Locality & bridges (structural)

From cluster locality and bridge-file evidence, if available. Structural
signals — strong on larger trees, low-signal on small/flat repos. What counts
as "many" or "scattered" is your judgment.

| Observation | Representation pressure toward |
|---|---|
| A cohesive cluster spread across many *peer* directories (shallow/root common ancestor, several top-level dirs) | Co-locating the scattered concept into one home |
| A cohesive cluster in one directory (or one dir + a root registration/config touchpoint) | Nothing — that is well-modularized; do not "fix" it |
| A cluster with wildly mixed depths (a 1-component dir among deep ones) | *Maybe* a misplaced or cross-cutting file — the softest signal; sometimes legit (a root config tied to deep code) |
| A bridge file connecting otherwise-separate groups | Investigate — it may be doing too much or be a leaky boundary; a legitimate shared core (base types, etc.) is a bridge too, so confirm before acting |

---

## Apply Zero-One-Many

Determine whether the current representation still fits the observed information.

The three meaningful cardinalities are **Zero**, **One**, and **Many**.
Specific numbers (2, 5, 7) are usually policy — they change. The transitions
between cardinalities are the design events that matter:

| Transition | What to reconsider |
|---|---|
| Zero → One | Does the concept need to exist at all? Where does it live? |
| One → Many | How is the collection represented? Who owns traversal? |
| Many → One | Can the collection collapse? Is there a canonical instance? |
| One → Zero | What disappears when the concept is absent? Is absence handled explicitly? |

At each transition, ask whether the existing representation can absorb the change
naturally. If not, improve the representation first.

Ask:

- Has something multiplied?
- Has variation increased?
- Has another owner appeared?
- Has another special case appeared?
- Has another repeated group appeared?

If not, preserve the current representation.

If so, determine what *kind* of multiplicity has emerged: more values, more
related values, more behavior, more implementations, more states, more rules,
more relationships, or more ownership sites.

Choose the smallest representation that naturally expresses the observed
information. Do not choose a representation because it is fashionable.

### Make the Change Easy (the constraint may live in a different feature)

The concept undergoing a cardinality transition is not always the file or
module you were asked to change. Implementing a new increment is sometimes
constrained by a *different*, already-existing feature that only handles one
case — one language, one backend, one format — where the new increment needs
several. The instinct is to work around that other feature from the outside:
special-case its absence, fork its logic beside the call site, or duplicate a
narrower version of it inline. Resist that instinct before accepting it.

This is Kent Beck's *Tidy First?* principle applied across feature boundaries,
not just within one: "for each desired change, make the change easy (warning:
this may be hard), then make the easy change." Apply the same One → Many
question to the constraining feature itself: can it absorb the new case
naturally if generalized? If extending it is small and evidently correct, do
that first — as its own preceding step — then implement the requested
increment as the easy, clean change on top of the now-general capability.
Prefer this whenever the "make it easy" step is no larger than the workaround
would have been: one owner of the capability instead of a duplicate living
beside it. This is not license to over-generalize — solve only the case the
current increment actually needs, inside the feature that owns the concept,
rather than beside it. (For sequencing this as its own step in a plan, see the
`demonstrable-increment-planning` skill's prerequisite-first ordering.)

---

## The Improvement Test

Before committing to a representation evolution, check whether the candidate
advances at least one virtue without regressing Working (the code must still
work) or introducing new violations of any virtue.

| Virtue | Question |
|---|---|
| **Unique** | Does this create a single point of maintenance where knowledge was duplicated or scattered? |
| **Simple** | Does this reduce operations, operands, or paths at the use sites? |
| **Clear** | Does this make intent more obvious — read in domain language, rather than reconstructed by simulating the mechanics? |
| **Easy** | Does this make the next similar change require less effort? |
| **Developed** | Does this give scattered primitives or behaviors an appropriate abstraction? |
| **Brief** | Does this express the same concept with less syntax at the call sites? |
| **Coherent** | Does this fit into and reinforce the existing vocabulary and patterns? Would someone who knows the rest of the system find it unsurprising? |

The evolution is warranted if it passes one or more of these and does not
introduce new violations.

If the candidate adds a new type, layer, or concept that passes none of these
tests — stop. The current representation is adequate, or the candidate needs
reconsideration. Prefer extending an existing owner over introducing a new one.

A signal in the pressure table indicates *pressure toward* a representation.
This test determines whether acting on that pressure produces a net gain.

---

## Refactoring Sequence

If representation pressure exists:

1. Improve the representation.
2. Move knowledge toward its natural owner.
3. Remove obsolete representations.
4. Simplify the surrounding code.
5. Then implement the requested behavior.

Prefer several small refactorings over one large redesign.

---

## Produce Recommendations

All output takes the form of recommendations. Do not silently apply changes.
Present findings first so the developer can confirm before implementation.

Each recommendation follows this structure:

| Field | Content |
|---|---|
| **Scope** | The specific location — file, class, function, variable — where the change applies |
| **Evidence** | The observations that identified representation pressure at this location |
| **Virtues harmed** | Which virtues are currently harmed by the existing representation |
| **Recommended change** | The representation evolution proposed — named precisely, not vaguely |
| **Virtues advanced** | Which virtues improve and why; what becomes easier as a result |

### Two modes

**Change mode** — when implementing new behavior or extending existing code:

Cover all touch points where the change lands. For each touch point, produce one
recommendation if pressure exists, or confirm the representation is adequate if it
does not. The developer should see the full surface of the change.

**Refactoring mode** — when improving existing code without adding behavior:

Do not enumerate every deficiency. Identify the three highest-value,
highest-confidence improvements and present those only. Rank by: strength of
evidence × expected virtue advancement. A change with strong evidence and clear
virtue gain outranks a speculative improvement with weak evidence.

Use history evidence as the *evidence-strength* axis of that ranking: prefer
improvements in files with high churn (the change will pay off more) and
pairs/clusters with high co-change scores (stronger evidence of a real shared
concept); use current-state signals (usage breadth, import graphs, recurring
literals) to pinpoint the representation pressure within them. Cite the scores
in the recommendation's **Evidence** field.

State why these three were selected over others observed. If fewer than three
improvements clear the Improvement Test, present only those that do.

---

## Constraints

Do not introduce abstractions without evidence.

Do not introduce design patterns directly — let patterns emerge from evidence.

Do not duplicate existing knowledge.

Do not recreate behavior already provided by the language, standard library,
framework, or existing domain model. Make this an **active check**: before
proposing or keeping any custom helper or inline block, name the language
feature or stdlib function that would do it; if one exists, prefer it, and state
the alternative you considered. Preference order:

> **standard library / language feature > an existing local function that
> already does the work > a new custom function > an inline block.**

Common reaches (not exhaustive — the linter is the backstop):
counting → `collections.Counter`; grouping → `itertools.groupby`; top-N →
`heapq.nlargest` or slicing; "everything" → `seq[:None]`; pairs →
`itertools.combinations`; accumulate → `itertools.accumulate` / `functools.reduce`;
memoize → `functools.lru_cache`; key functions → `operator.itemgetter` /
`operator.attrgetter`.

### Iteration & collection

Choose the simplest construct that correctly expresses the lifetime of the data.
Selection order:

1. **Comprehension** — simple collection construction.
2. **Generator expression** — single-pass lazy pipelines.
3. **Generator function (`yield`)** — stateful or complex lazy sequences.
4. **Iterator class** — only when external iterator state or rich iterator
   behavior is required.
5. **Plain `for` loop** — when the primary purpose is side effects.

`./check` already enforces the mechanical half (append loop → comprehension,
temp list → generator inside a call, needless `list(...)`; ruff `PERF`/`C4`).
This clause is for what the linter cannot judge:

- Materialize a collection only when multiple passes, random access, ownership,
  or an API demand it; otherwise keep the lazy pipeline.
- Keep comprehensions simple — extract a named helper for complex logic, and
  prefer named helpers over complex inline expressions.
- Never use a comprehension for its side effects; use a `for` loop. (ruff does
  not catch this — catch it in review.)

Preserve the current architecture unless the evidence indicates that the
representation should evolve.

---

## Review Before Finishing

Before presenting the result, answer:

- What concept changed?
- What evidence identified that concept?
- Did the representation evolve?
- Did ownership become clearer?
- Did the overall representation of the concept become simpler?
- Is the next similar change likely to require less work?
- Is the concept's intent expressed top-down in domain language, or must the
  reader play compiler to recover it?

If the representation became more complicated without clear evidence that it
needed to, reconsider the design before producing the final solution.
