---
name: unit-testing
description: Implement or extend production behavior test-first, or diagnose focused unit-test quality and flakiness, using red-green-refactor, ZOMBIES, Tidy First?, FIRST microtests, and Save Your Game checkpoints. Use for TDD, microtests, test-first bug fixes, flaky tests, and refactoring within an active green cycle. Do not use to choose delivery slices, format user stories, conduct a broad representation review, or perform a focused identifier-naming analysis; those belong to the corresponding sibling skills.
---

# Unit Testing (TDD · Microtests · ZOMBIES · Tidy First? · Eight Virtues)

## When to use this skill

**Use `unit-testing` when:**
- Implementing new behavior or extending existing behavior with production code
- Bug fixes that require new logic (characterize with a failing test first)
- Choosing the next test to write (ZOMBIES ordering)
- Deciding whether to tidy before writing the next test (Tidy First?)
- Refactoring production or test code toward the Eight Code Virtues within an active TDD cycle
- Diagnosing flaky, slow, or poorly-structured tests using FIRST
- Any session where you would otherwise "code then sprinkle tests"

**Do NOT use `unit-testing` for:**
- Establishing initial test access or characterizing poorly understood existing behavior → use `legacy-code-safety`, then return here
- Choosing which delivery slice to build next → use `story-splitting-for-delivery`
- Formatting an already-split story as user-visible outcomes → use `user-pov-sliced-stories`
- Reviewing code broadly for representation or virtue violations without an active TDD cycle → use `representation-refactor-review`
- Performing a focused identifier diagnosis or rename plan → use `code-object-naming`
- Trunk-landing strategies, feature toggles, or branch-by-abstraction (out of scope for this package)

---

## Purpose and scope

TDD is programming hygiene. Its job is not "prove the whole system" or "raise coverage." Its job is to keep code orderly and **safe to change in tiny steps** so you can refactor, integrate, and deliver without fear.

- **Timely, not Thorough:** test-first keeps code testable and orderly; component, contract, E2E, and human testing are still required and not replaced by microtests.
- **Test-after is not TDD:** writing tests after a production pile recreates legacy conditions — hard-to-test shapes, fear of breaking "what already works," and joyless test-after work.
- **Review is not a substitute for tests:** `representation-refactor-review` catches representation drift and virtue violations but does not replace the microtest hygiene loop this skill owns.

---

## What requires test evidence

Before changing production behavior, make a short **Beck-style test list** of
behavioral examples and concerns. This is not a manual test plan or a scripted
series of human actions and observations. It is a revisable list of tests that
might be needed; implement only one test at a time and update the list as the
code teaches you more.

A test list is required when work creates or changes:

- decisions or alternatives: `if`/`else`, conditional expressions, pattern
  matching, `switch`/`case`
- repetition, selection, grouping, ordering, or aggregation:
  `for`/`while`, filters, folds, queries
- calculations, conversions, parsing, formatting, or validation
- documents, classes, records, messages, entities, or other data
- persistence, retrieval semantics, state transitions, or side effects
- error handling, retries, fallbacks, authorization, or boundary enforcement
- any behavior where different inputs, states, or circumstances should produce
  meaningfully different results

At minimum, consider and list:

- ordinary successful examples
- anticipated errors and rejected inputs
- boundary conditions and transitions

The test list is inventory, not a batch to write in advance. Select the next
test with ZOMBIES, make it pass, refactor, and then reconsider the list.

### Choose the test level

Decision and transformation logic normally belongs under FIRST microtests.
Behavior that depends on a real boundary needs the smallest faithful automated
test capable of establishing it:

- persistence semantics may require an integration test against the real store
- document creation may require a component, approval, schema, or round-trip test
- messages and public interfaces may require contract or serialization tests
- user workflows may require story, component, or end-to-end tests

Extract decision or transformation logic into microtestable units when that
improves the design. Do not replace necessary high-fidelity evidence with mocks
that cannot establish the real behavior.

Dedicated microtests are usually unnecessary for simple wiring or delegation,
read-only accessors that merely return stored state, generated code, trivial
data carriers, or declarative framework configuration. These may be exercised
indirectly by a faithful higher-level test. Add focused tests when apparently
simple code acquires a decision, transformation, contract, or meaningful
failure mode.

---

## Preconditions: Clean Start

Before the first production edit of a task:

1. Working tree intentional and tidy — no mystery untracked junk, no unrelated half-work.
2. Current with the integration branch when project practice and the user's authorization allow the required fetch/pull.
3. Dependencies updated the repo's way.
4. Clean build if the stack needs one.
5. **All relevant tests green** — use `./prepare` or `./run_tests` when present.

If anything is red before your changes, stop. That is an inherited problem; do not pile new work on a broken baseline.

Run the fast suite after each small step. Testing never needs permission.

---

## The cycle (do not skip steps)

Work one behavior at a time. Keep cycles short enough that retreat is cheap.

```text
clean/green baseline
  → update the Beck-style test list; pick ONE next behavior (ZOMBIES order)
  → Tidy First? (First / After / Later / Never)
  → write the next failing test at the chosen level (normally a microtest)
  → write minimum production code to pass (green)
  → refactor toward the Virtues (stay green)
  → authorized atomic microcommit (Save Your Game)
  → integrate: combine, verify, publish when authorized
  → repeat from a clean, current baseline
```

### Red

- Name the behavior in domain language (situation + expectation).
- Exercise a realistic public API you wish existed; let the test design the call site.
- Fail because the behavior is missing or wrong — **not** from `fail()` hacks or compile errors as placeholders.
- Only enough test to fail meaningfully. One primary reason to fail; clear assertion message.

### Green

- Only enough production code to make the suite pass.
- No speculative features; no extra branches "while you're here."
- You may change design for testability; that is expected.
- When anything is red, your only job is restoring green — including **graceful retreat** to the last good commit if the step went sideways.

### Refactor

- Required, not optional. Skipping refactor is how suites and designs rot.
- Remove duplication; clarify names; improve structure **while green**.
- Refactor tests too; treat them as production-grade code.
- Prefer automated IDE/LSP refactor tools over manual cut/paste.
- Stay structure-shy (see below) so tests do not freeze internals.

### Atomic microcommit / Save Your Game

- When the intentional step is complete and green, use `atomic-commit` to prepare the whole repository state, obtain human review, and commit only when authorized.
- The atomic microcommit is the local **Save Your Game** point: coherent, tested, recoverable, and distinct from publishing to collaborators. Human review belongs inside this rapid loop; do not enlarge the step merely to reduce review frequency.
- Park side quests instead of mixing them. Before tricky attempts, use an authorized recoverable checkpoint. If confused, retreat without discarding unrelated user work, then redo smaller.
- If a commit is not authorized, preserve and report the green diff without committing.
- Task is not complete while tests fail.

### Integrate

- Integration is a separate step after the local Save Your Game point: obtain current shared changes, combine them with the completed change, and rerun the prescribed checks on that newly combined state.
- Publish only when project practice calls for it and the user has authorized the external action.
- Any integration operation that creates or rewrites commits remains subject to the complete-state review and verification rules in `atomic-commit`.
- Do not call a local commit "integrated" when collaborators cannot yet obtain it. Do not publish a combined state that has not been tested.

---

## ZOMBIES: ordered test selection

Maintain the Beck-style test list. Pick the next test using ZOMBIES, not arbitrarily:

1. **Zero** — the null/empty/trivial case first.
2. **One** — a single simple instance.
3. **Many (More complex)** — the general case, once Zero and One both pass.
4. At each of those stages, separately attend to:
   - **Boundary** — edge values at that complexity level.
   - **Interface** — does the shape of the call still make sense as scenarios accumulate?
   - **Exception** — the failure/error path for that stage.
5. **Simple scenarios, Simple solutions** — resist writing a Many-complexity test while Zero/One are unproven. Resist over-engineering the implementation ahead of what the current test demands.

**One test at a time.** Never write a batch of tests and fill them in after — batching commits to interface decisions before the first implementation has taught you anything. Canon TDD names this a failure mode (rework, "test #6 depression") for a concrete reason.

---

## Tidy First? (before each next test)

Before writing each next test, ask explicitly: **First, After, Later, or Never?**

- **First** — current structure would make the upcoming test awkward or impossible to add cleanly. Do the structural change now, as its own step: tests green before and after, no behavior change, separate commit from the behavior that follows. This is "make the change easy, then make the easy change."
- **After** — structure is fine for this test; land the behavior now, clean up in the refactor step once green.
- **Later** — worth doing eventually, not blocking right now. Note it (comment, ticket, journal — whatever the project already uses) and proceed.
- **Never** — the cost of tidying exceeds the benefit. Say so and move on; don't tidy reflexively.

Prefer LSP-backed rename/extract tools or `ast-grep` structural rewrite over hand-editing for any First or post-green structural change — mechanical and deterministic beats agent-reasoned-and-regenerated for moves a tool can do exactly. Reserve model reasoning for the judgment call (which option, and why), not for typing out a rename across a dozen call sites.

---

## Microtests (FIRST)

TDD's inner loop uses **microtests** (unit tests that meet FIRST):

| Letter | Meaning |
|--------|---------|
| **F**ast | Milliseconds preferred; no real network/DB/filesystem/clock/services |
| **I**solated | No shared mutable state; any order; one behavior |
| **R**epeatable | Same result every run; control time/randomness/threads |
| **S**elf-verifying | Assert automatically; no manual log inspection |
| **T**imely | Written before/with the code, not after a big bang |

Rules of thumb:

- Test the unit in an **artificial** context, not full app context.
- If you need DB/HTTP/clock, fake or inject them — or move this test to a slower suite.
- Do not grow a heavyweight test framework to compensate; shrink the test and the unit boundary.
- Microtests do not replace component, contract, story/BDD, E2E, or human checks. They make those affordable by keeping units honest.
- **High-fidelity rule:** production code must not branch on "am I being tested?"

### Make Isolated and Repeatable observable

FIRST is an acceptance criterion, not merely a description. Before accepting a
new or changed test as green, inspect every input that can affect its assertion:
time and timezone, randomness, threads and scheduling, iteration order, process
environment, locale, shared mutable state, files, ports, databases, networks,
credentials, permissions, and pre-existing records. The test must control each
relevant input or provide an isolated, test-specific environment that does.

Use evidence proportional to the risk:

- Run the new test alone and in its containing suite.
- When the runner supports it, vary test order to expose contamination and
  retain the reported seed so a failure can be reproduced. Ordering tests to
  hide contamination is not a repair.
- For a concurrency, timing, order-dependence, or prior-flake repair, repeat the
  focused test enough to investigate likely intermittency. Repetition supplies
  evidence; it does not prove that no flake remains and must never become
  rerun-until-green acceptance.

Whatever a test requires, it provides. Prefer fresh fixtures and unique,
test-owned resources. For higher-level tests that need real infrastructure,
provision known configuration and curated data in a pristine or otherwise
isolated environment; do not share mutable services with people or unrelated
test runs.

Assert only the behavior that matters. Do not depend on incidental order from
unordered collections, queries, messages, or concurrent completion: either make
ordering part of the production contract or compare without regard to order.
Prefer explicit deterministic inputs; when randomness is itself relevant, use
a reproducible seed and report it on failure. Use one injected clock reading for
one logical operation and deliberately cover relevant calendar, timezone, DST,
and expiry boundaries. Synchronize on observable events, conditions, futures,
or barriers rather than guessed delays; assert elapsed time only when timing is
the behavior under test.

### Outside-in option

A failing higher-level example/story test may hang red while you drive the interior with microtests. Still do not bulk-write production code without microtest guidance for decisions and transformations.

---

## Write tests that enable refactoring (structure-shy)

Bad tests block the purpose of TDD.

**Behavior over structure**

- Read tests to understand code; never require reading production code to understand tests.
- Assert observable results and meaningful outcomes, not incidental private structure.
- Prefer scenario-oriented organization (shared arrange = shared situation) over rigid "one test class per production class" when clarity suffers.

**Resilient under routine change**

Existing tests should normally survive implementation edits and refactorings
that preserve observable behavior. Do not mechanically edit tests to mirror each
production edit or merely restore green. When an existing test breaks, classify
the reason before changing either side:

- The observable behavior or contract intentionally changed: update or replace
  the test deliberately so it states the new behavior.
- Production behavior regressed: repair the production code.
- Only implementation structure, incidental formatting or ordering,
  collaborator calls, snapshots, or fixture details changed: repair the
  over-specified test so it observes the meaningful outcome instead.
- The reason is unclear: investigate before editing both test and production
  code; making both agree can conceal the defect.

If routine work requires edits to several existing tests, stop treating those
edits as maintenance. This is evidence of shared structural coupling or
over-specification. Locate and remove that source of maintenance pressure before
continuing. Adding a test for genuinely new behavior is expected; repeatedly
rewriting existing tests to track code movement is not.

**Structure-shy (Law of Demeter / "one dot")**

- Do not reach through deep graphs in tests or production (`a.b.c.d`).
- Talk to immediate collaborators; push knowledge behind intention-revealing methods.
- Deep coupling in tests makes refactors fail everywhere and teaches teams to fear improvement.

**Assertions and names**

- Use assertions that print useful expected/actual values.
- Test name + assertion should diagnose the mistake without reading the whole test body.
- Avoid magic values; name domain-meaningful constants.

**Side effects**

- Prefer testing direct results over obscure global/file/DB side effects.
- Side-effect-heavy tests usually signal low-cohesion design — improve the design.

---

## Refactor toward the Eight Virtues

When refactoring (optionally after each green; required in CLEANUP), target named virtues rather than vague "cleanup":

**Working** is non-negotiable. **Unique, Simple, Clear, Easy, Developed, Brief, and Coherent are peers in balance**; no peer has a fixed rank. Never pursue Brief at the expense of Working or overall representation quality.

- **Unique / SPOT** — is this fact stated in exactly one place? Duplication hints at a Unique violation. Do not abstract ahead of a real second instance.
- **Simple** — fewer operators/operands/paths, independent of naming.
- **Clear** — would multiple readers agree on what this does, independent of Simple.
- **Easy** — is the right next change actually easy to make, or would it require touching many places?
- **Developed** — still using raw primitives where a real type/abstraction has emerged? (Watch for Primitive Obsession, Feature Envy.)
- **Coherent** — does this vocabulary, pattern, and structure agree with the rest of the system, not just read well in isolation? Especially useful for keeping agent-written code from drifting into locally-sound-but-globally-inconsistent vocabulary.
- **Brief** — remove excess that adds no value, while balancing it with Clear, Easy, Developed, and the other peers.

Use LSP rename / `ast-grep` for mechanical moves (Extract Method, Rename, Replace Temp with Query — Fowler's catalog); use model judgment only to decide *which* virtue is violated and what the target shape should be.

---

## Affordable feedback

Defect cost tracks how long bugs sit undetected. Slow suites make people run tests less, which makes debugging worse.

- Keep the coding suite fast enough to run after nearly every edit.
- Segregate slow tests; do not pretend UI/API tests are microtests.
- Replace slow broad tests of pure logic with microtests of that logic.
- Flaky tests destroy trust — fix causes (over-specification, shared state, time, external services, order dependence). Do not normalize "rerun until green."

---

## Diagnosing FIRST violations

| Symptom | Likely violation | Common root causes |
|---------|-----------------|-------------------|
| Fails intermittently | Repeatable | Clock, threads, randomness, env difference |
| Passes alone, fails in suite | Isolated | Shared state, static caches, DB residue |
| Fails only in CI | Repeatable | Env config, concurrency, race conditions |
| Slow and unstable | Fast | Real network/DB calls, large fixtures |
| Unclear failure signal | SelfVerifying | Missing/weak assertions, log-inspection reliance |

Repair approaches: inject clock abstractions; seed RNG; use synchronization primitives (remove `sleep()`); reset state in setup/teardown; eliminate globals; replace real services with in-memory fakes or doubles.

Do not assume the test is defective. A consistent test can reveal intermittent
production behavior such as races, lost updates, nondeterministic ordering,
overflow, clock-boundary defects, or latency sensitivity. Reproduce while
varying one relevant dimension at a time (order, seed, load, timezone/locale,
parallelism, or environment), locate the uncontrolled input, and repair the
cause. Do not weaken, ignore, quarantine, or rerun past the assertion merely
because the failure is intermittent.

---

## What TDD is not (avoid cargo cult)

| Misunderstanding | Reality |
|-----------------|---------|
| TDD = QA / system validation | TDD enables safe change; other testing still required |
| TDD = maximize coverage % | Coverage is a side effect; goal is safe change |
| Write all tests first in a batch | One failing test at a time, in cycle |
| Testers hand devs unit tests | Developers own the microtest cycle and refactor |
| Skip green/refactor because "trivial" | Small skips accumulate into untestable mess |
| Integration is "not TDD" | Save locally, then integrate continuously; verify the combined state |
| Tests must mirror class structure | Tests must document behavior and survive refactor |
| Timely means Thorough | Write tests when writing the code; exhaustive coverage is not the goal |

---

## Session algorithm

1. **Clean start** — baseline green (`./prepare` / `./run_tests` as available).
2. **Test list** — inventory likely successes, errors, and boundaries; do not write the tests as a batch.
3. **Tidy First?** — ask First/After/Later/Never before each next test.
4. **Pick one** behavior; optionally draft the commit message (intentional commit).
5. **Red** — write the next test at the chosen level (normally a FIRST microtest); confirm its failure reason is correct.
6. **Green** — minimal code; run tests (full fast suite or project norm).
7. **Refactor** — tidy prod + tests toward named virtues; run tests again. If behavior-preserving production edits break existing tests, classify the cause and remove over-specification rather than synchronizing tests mechanically.
8. **Atomic microcommit / Save Your Game** — when authorized, use `atomic-commit` to review and preserve the complete green state; otherwise report the green diff.
9. **Integrate** — when authorized, incorporate shared changes, verify the combined state, and publish; do not conflate this with the local commit.
10. If stuck more than one small step of confusion → **retreat** to the last green saved state and choose a smaller behavior.
11. Repeat from a clean, current baseline. Never end a coding session on red you introduced.

---

## Anti-patterns to refuse

See `references/anti-patterns.md` for the quick-reference list. Key ones:

**Process:** production code before a failing test; big-bang implementation then tests; skipping refactor; batching tests before implementing any; leaving suite red while starting another concern; huge uncommitted WIP; normalizing "rerun until green."

**Test design:** tests coupled to private structure or deep-graph navigation; routinely editing existing tests to mirror production changes; one test asserting many unrelated behaviors; shared mutable fixtures leaking across tests; real time/network/DB/filesystem/sleep in microtests; production code that detects test mode; test names that restate technical methods instead of domain situations.

**Refactor:** vague "cleanup" without targeting a named virtue; hand-editing renames across many files when LSP/`ast-grep` can do it exactly; pursuing Brief at the cost of Clear or Working.

**Scope confusion:** expecting microtests alone to prove product fitness; treating coverage % as the goal; weakening or rewriting existing tests to accept broken behavior without explicit human approval.

---

## Interaction with other skills

- `legacy-code-safety` — establishes a trustworthy boundary around poorly understood or weakly tested existing code. Once that boundary can detect relevant change, this skill owns the new behavior cycle.
- `story-splitting-for-delivery` — choose and sequence thin vertical delivery slices; `unit-testing` implements each admitted slice with TDD discipline. Do not use `unit-testing` to choose the split.
- `user-pov-sliced-stories` — formats an already-split story as explicit User-invokes / User-uses-result outcomes. `unit-testing` does not own that formatting.
- `representation-refactor-review` — owns broad representation critique, including ZOM drift. The Eight Virtues vocabulary is shared: `unit-testing` applies it inside the active green cycle; the review skill applies it when review itself is the task.
- `code-object-naming` — owns focused identifier diagnosis and rename planning. Routine naming improvements inside the green refactor step remain part of `unit-testing`; defer only a deeper naming pass.
- `atomic-commit` — owns preparation, whole-repository verification, human review, and creation of the local Save Your Game microcommit. `unit-testing` keeps that commit distinct from subsequent shared integration.
- **Existing tests are contracts:** do not weaken or rewrite existing tests to accept broken behavior unless the user explicitly approves and reviews the shown change.
