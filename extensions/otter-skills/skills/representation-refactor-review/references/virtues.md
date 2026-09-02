# The Eight Code Virtues

Tim Ottinger and Jeff Langr's positive vocabulary for code goodness (from *Agile in a Flash*, expanded over years, unified as the Eight Code Virtues). Where code smells name what is *bad*, the virtues name what is *good*—so a reviewer can say precisely what to preserve and what to pursue.

Canonical write-up: [Eight Code Virtues (draft)](https://agileotter.blogspot.com/2026/08/eight-code-virtues-draft.html).

## How the virtues relate

**Working is non-negotiable.** The other seven are peers evaluated **in balance**, not a strict ladder:

> **Working** (prime) · **Unique · Simple · Clear · Easy · Developed · Brief · Coherent** (peers)

Never sacrifice Working for any other virtue. Among the peers, do not automatically rank one above another. Prefer changes that improve **several** virtues at once, usually by finding a better representation of knowledge. When peers pull against each other, use judgment and the improvement test—not a fixed ordering.

### The improvement test

Any proposed change must answer:

1. Does it preserve **Working**?
2. Given that it works, is the resulting code **really better** when Unique, Simple, Clear, Easy, Developed, Brief, and Coherent are considered **together**?

If not, revert or try something smaller. Completing a refactoring that leaves the software worse is not virtuous.

### Evidence, subjectivity, and judgment

Not all virtues are subjective:

| Virtue | Character |
| --- | --- |
| Working, Unique, Simple, Developed, Brief, Coherent | Observable; can be evidenced (with investigation) |
| Clear, Easy | Subjective—relationships (readers; change + people/tools/system) |

**Objective does not mean trivial to score.** Shared knowledge may be non-obvious; evidence can be incomplete; first interpretations can be wrong.

An observation that a virtue is under pressure **does not prescribe the refactoring**. Several fixes may address the same pressure and affect other virtues differently. Separate:

- **Observations** — what the code shows
- **Inferences** — what that may mean (hypotheses)
- **Actions** — the smallest representation change worth trying

---

## 1. Working — *as opposed to incomplete / unproven*

The code has to work. Working is not design taste. We may accept a little duplication for clarity or extra lines for ease—we do **not** trade away Working.

"Working" means more than looking plausible. Compilation yesterday, a single green test long ago, or author confidence is weak assurance.

- Prefer fast, useful automated tests run **before and after** changes.
- Also learn from demos, experiments, monitoring, and real use.
- Without behavioural evidence, "refactoring" becomes wishful rewriting.
- If tests are missing or thin: characterise behaviour, find a seam, or make careful preliminary changes so important behaviour can be observed—especially under agentic change.

**Review implications:** Establish this first. Missing/failing tests for code under change, untested rewrites, and "it should work" are P1. Without Working, no other virtue is interesting.

## 2. Unique — *as opposed to duplicated knowledge*

**SPOT (Single Point of Truth):** each piece of knowledge should have **one authoritative representation**. Prefer SPOT over dry "don't repeat text," because the hazard is repeated *truth*, not identical characters.

- Two identical values may be different facts that happen to match today—merging them would couple independent change.
- Duplication is often non-textual: the same rule as calculation, conditional, comment, config, UI list, and test fixture.
- Example: payment methods as enum + UI list + config strings + validation branches + serialisation maps + fixtures—different text, same knowledge.
- Ask: would these have to change together because they express the same fact or rule? If yes, one authoritative home; derive the rest.
- Heuristics: version history of co-change; text/dupe detectors (with known limits).

**Review implications:** Duplicated facts/algorithms and implicit shared assumptions are P1 when they can silently corrupt behaviour under maintenance.

## 3. Simple — *as opposed to complicated*

Simple is a **structural** property: fewer **operands**, **operations**, and **execution paths** for the same behaviour at the same scope.

- Not familiarity, fashion, or "only elementary features." Those may aid Clear or Coherent; Simple is literal machinery count.
- A long procedural familiar solution can still be high in operands/ops/paths.
- Tables can replace long conditional chains (one lookup vs many decision paths).
- Collections replace `item1`/`item2`/`item3` coordination.
- Named state replaces boolean soup and invalid-combination logic.
- Named types replace primitive clusters passed and manipulated together.
- Extracting a function may simplify **local** structure without reducing overall ops/paths—still useful locally; judge overall honestly.
- Patterns/abstractions add their own structure; keep them only when what they remove exceeds what they add.

**Review implications:** Count operands, operations, paths—make measurable claims. High path complexity is typically P2. Prefer reductions of real machinery, not ceremony for its own sake.

## 4. Clear — *as opposed to puzzling*

Clear code communicates with its **intended readers**. Maintainers are the real audience. Code is always clear to the author at write time; the virtue is clarity for **non-authors** in that audience—not imaginary beginners who know nothing of language, domain, or system.

- Clarity is contextual and **subjective to the group**.
- Idioms, domain terms, and local conventions reduce surprise.
- Agents are often good at following local patterns—use that.
- Clarity is more than restating mechanics in comments; better names/representations say *why* and *how it belongs*.

**Review implications:** Name clarity findings as subjective but argue from audience and idioms. Disinformative names, not-logic, and reverse-engineering chores are usually P2.

## 5. Easy — *as opposed to difficult to change*

Easy is about **change**, not reading. Understandable code can still make an ordinary change hard.

- Best moment to tend Easy: **just before** a known feature change—refactor so the change fits, then make the change (Beck). That is not speculative futures.
- Speculative extension points for features that never arrive add structure without benefit and may block the real future.
- Tables make "one more case" a row, not surgery on control flow.
- Named/extracted policies and constants give change a home (e.g. limit `3` scattered vs one policy).
- Dead branches and leftover feature flags force reasoning about decisions that no longer exist.
- Co-change history, recurring repair commits, and scatter are evidence of awkward homes/boundaries.

Improvements to Easy often improve Simple, Brief, Unique, Clear, or Coherent at the same time.

**Review implications:** Ask what change is imminent and how hard it is. Structure that resists likely change is typically P3 (P2 if change is frequent/imminent). Prefer evidence-backed prep over speculative architecture.

## 6. Developed — *as opposed to primitive*

Programs start from language primitives. As understanding grows, the program should grow **concepts of its own**.

- Variables that travel together in args, loops, and branches often hide an undeclared type.
- Functions that only operate on that group are candidate operations of the type.
- Goal is not "classes for classes' sake"—it is representing a concept the program already repeatedly assembles.
- A better type often shortens arg lists, homes operations, speaks domain language, and reduces mishandling—improving Unique, Simple, Clear, Easy, Brief, and Coherent together.
- When a concept keeps reassembling itself, the program is asking for a name.

**Review implications:** Point at the primitive cluster and name the type/home. Usually P2–P3. Often a SPOT win.

## 7. Brief — *as opposed to chatty / low signal*

Brief means high **signal-to-noise** for the same behaviour and information—not fewest characters, not code golf.

- Cryptic short code fails Clear/Easy and is not a win.
- Denser idioms (filter, comprehension, map) can replace loops/collectors and be *easier* to grasp at a glance.
- Small functions replace repeated explanation; better representations delete whole categories of plumbing.
- Do not discount Brief or confuse it with golf.

**Review implications:** On its own, often P3–P4. Over-terse cleverness is a **clarity** defect. Prefer representation that removes noise without hiding information.

## 8. Coherent — *as opposed to contradictory dialects*

**Coherence** is how far concepts, vocabulary, abstractions, architecture, patterns, and representations **reinforce** one another.

- In a coherent system, learning compounds: understanding one part helps elsewhere.
- Names stay consistent; similar relationships use similar forms; new work strengthens the system's language rather than inventing a local dialect.
- Close partner of Developed: enum vs strings vs subclasses vs flag clusters for "the same" concept may be four dialects—or legitimately different models. Compare meanings/boundaries before forcing unity.
- Flags may be unnamed state; primitive groups unnamed concepts; long conditionals knowledge better as table, rules, map, graph, or state machine.
- Coherence is **not** "everything looks the same." One forced pattern can be consistent and still make little sense.
- Before adding abstraction: how does this system already express similar ideas? Extend the language or invent another way to say the same thing?

**Review implications:** Conflicting dialects for the same knowledge, pattern thrash, and vocabulary drift are typically P2–P3 (P1 when they encode competing truths that break Unique/Working). Prefer reinforcing existing good language over novel local styles.

---

## Comments and the virtues

Comments are not executable. They can prime readers for hard algorithms, constraints, workarounds, or rationale the language cannot carry—and they can hide design problems.

Three rules:

1. Comments are for things that **cannot** be expressed in code.
2. Comments that **restate** the code must be deleted.
3. If a comment says what the code could say, **change the code** so the comment is redundant, then delete it.

Moving comment knowledge into names/types/functions improves Unique, Clear, Simple, Developed, Brief, Coherent, and sometimes Easy. Do **not** strip comments from difficult code before improving representation—that leaves the same difficulty with less help. Temporary learning comments can guide refactoring, then go.

---

## From virtues to refactoring (review + change)

1. Treat smells, metrics, awkward changes, and surprising search hits as **reasons to investigate**, not orders.
2. Start from code involved in the **real** change. Search names/terms; find constants, enums, branches, structures, tests; look for traveling values; learn local vocabulary; use history when helpful.
3. Inspect comments (restate? obsolete? promotable to code? indispensable rationale? temporary scaffolding?).
4. Ask whether the concept has **one owner**. Prefer the smallest representation that gives it one.
5. Separate observation / inference / proposed action; name virtues under pressure and tradeoffs.
6. Small behaviour-preserving steps; tests green; structural commits separate from behavioural ones. Strengthen safety evidence before broad refactoring.
7. Re-evaluate with the improvement test. If not better overall—revert.

---

## Using the virtues in a review

- Confirm **Working** first; then evaluate the seven peers **together**.
- Tag each finding with the virtue(s) under pressure.
- For objective virtues, make evidence-backed claims (counts, clusters, co-change, competing representations).
- For Clear and Easy, say they are subjective and argue from audience, idioms, and the actual change.
- Prefer findings that point to a **representation** improvement affecting multiple virtues.
- The virtues describe goodness; they complement SOLID and the 4 Rules of Simple Design (see `architecture.md`)—they do not replace them.

## Further reading (selected)

- Ottinger & Langr — How Virtuous Is Your Code? (original seven)
- Ottinger — 7 Code Virtues Explained; Time for an 8th Virtue: Coherence
- Sciamanna & Ottinger — SPOT and Coincidental Duplication
- Ottinger — Simple v. Complicated; Rethinking Readability; Meaningful Names Revisited
- Fowler — Refactoring; Feathers — Working Effectively with Legacy Code
