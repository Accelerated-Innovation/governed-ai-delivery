# 7 Code Virtues Scoring Rubric — Backend

Each virtue is scored 1–5 per implementation increment. The minimum acceptable average across all seven virtues is **4.0**. Any individual score below 3 is a blocking failure regardless of average.

---

## Working

| Score | Criteria |
|-------|----------|
| 5 | All tests pass. All edge cases identified in the spec are handled. No runtime errors under expected inputs. Error paths return domain-appropriate results. |
| 4 | All tests pass. Most edge cases handled. Minor edge cases (e.g., empty collections, boundary values) may lack explicit handling but do not cause errors. |
| 3 | All tests pass. Some edge cases unhandled — they produce acceptable but suboptimal behavior (e.g., generic error instead of specific). |
| 2 | Most tests pass. One or two failures related to unhandled edge cases or incomplete implementation. |
| 1 | Tests fail on core functionality. Runtime errors on expected inputs. Incomplete implementation. |

**Key question:** Does the code do what the spec says it should, including edge cases?

---

## Unique

| Score | Criteria |
|-------|----------|
| 5 | Zero duplicated logic. Shared patterns extracted into reusable functions or classes. No copy-paste code. |
| 4 | No meaningful duplication. Minor structural similarities exist (e.g., similar error handling in two places) but logic is not duplicated. |
| 3 | One instance of duplicated logic (2 occurrences). Extraction is feasible but not urgent. |
| 2 | Multiple instances of duplicated logic (3+ occurrences). Clear candidates for extraction exist but were not addressed. |
| 1 | Pervasive copy-paste. Same logic repeated across files with minor variations. |

**Key question:** If this logic needs to change, how many places must be updated?

---

## Simple (Structural Simplicity)

| Score | Criteria |
|-------|----------|
| 5 | Maximum nesting depth <= 2. Cyclomatic complexity <= 5 per function. No mutable state beyond loop counters. Straightforward data flow. |
| 4 | Maximum nesting depth <= 3. Cyclomatic complexity <= 7 per function. Minimal mutable state, well-contained. |
| 3 | Maximum nesting depth <= 4. Cyclomatic complexity <= 10 per function. Some mutable state but manageable. One or two functions could be simplified. |
| 2 | Nesting depth > 4 in places. Cyclomatic complexity > 10 in some functions. Multiple flags or state variables controlling flow. |
| 1 | Deeply nested logic. High cyclomatic complexity (> 15). Interleaved concerns. Difficult to trace execution path. |

**Key question:** Can a developer understand what this function does by reading it once, top to bottom?

---

## Clear

| Score | Criteria |
|-------|----------|
| 5 | All identifiers are descriptive and domain-aligned. Functions do one thing. No explanatory comments needed — the code reads as prose. |
| 4 | Identifiers are descriptive. Functions are focused. Rare comments explain non-obvious domain logic (not what the code does, but why). |
| 3 | Most identifiers are clear. One or two functions do more than one thing but are internally coherent. Occasional abbreviations that aren't immediately obvious. |
| 2 | Some cryptic identifiers (single letters, abbreviations). Functions mix concerns. Comments needed to understand basic flow. |
| 1 | Unclear naming throughout. Functions are large and multi-purpose. Code requires significant comments or external documentation to understand. |

**Key question:** Can a new team member understand this code without asking the author?

---

## Easy (Maintainability)

| Score | Criteria |
|-------|----------|
| 5 | Loose coupling — components interact through ports/interfaces. High cohesion — each module has a single clear responsibility. Clear extension points for future changes. |
| 4 | Good separation of concerns. Dependencies flow inward (hexagonal). Minor coupling exists but is contained within a single layer. |
| 3 | Mostly well-structured. One or two cross-layer dependencies that could be refactored. Extension requires moderate effort. |
| 2 | Tight coupling between layers. Changes in one module frequently require changes in others. Extension requires significant refactoring. |
| 1 | Monolithic structure. No clear boundaries. Changes have unpredictable ripple effects. |

**Key question:** Can this code be modified or extended without breaking unrelated functionality?

---

## Developed (Test Coverage & Hygiene)

| Score | Criteria |
|-------|----------|
| 5 | All public behavior has tests. Dead code removed. Consistent style throughout. No TODO or FIXME markers left from implementation. |
| 4 | All public behavior has tests. Style is consistent. Minor dead code or one TODO with a tracked issue. |
| 3 | Most public behavior has tests. Some internal helpers lack coverage. Style is mostly consistent. |
| 2 | Test coverage is partial. Significant public behavior untested. Inconsistent style across files. |
| 1 | Minimal or no tests. Dead code present. Inconsistent style. Unresolved TODOs scattered throughout. |

**Key question:** Is this code production-ready, or does it still need cleanup?

---

## Brief

| Score | Criteria |
|-------|----------|
| 5 | No redundant comments. No speculative abstractions. No unnecessary boilerplate. Every line serves the current requirement. |
| 4 | Minimal unnecessary code. One or two comments that restate the obvious but don't harm readability. |
| 3 | Some unnecessary code — an unused import, a commented-out block, or a premature abstraction that adds complexity without current value. |
| 2 | Multiple instances of unnecessary code. Speculative abstractions (e.g., generic factory for a single implementation). Verbose boilerplate. |
| 1 | Significant bloat. Large commented-out sections. Multiple abstractions serving hypothetical future requirements. Code-to-value ratio is poor. |

**Key question:** If I deleted this line/function/class, would anything break?

---

## Applying This Rubric

1. Score each virtue 1–5 for the implementation increment under review
2. Calculate the average across all seven virtues
3. **Pass:** average >= 4.0 AND no individual score below 3
4. **Fail:** average < 4.0 OR any individual score below 3
5. Record scores in the feature's `plan.md` evaluation_prediction block during planning, and validate against actuals during review

---

## Refactor Triggers

Any of these conditions should trigger an immediate refactor before proceeding to the next increment:

| Trigger | Related Virtue | Threshold |
|---------|---------------|-----------|
| Duplicated logic (3+ occurrences) | Unique | Score drops to 2 |
| Cyclomatic complexity > 10 per function | Simple | Score drops to 3 |
| Nesting depth > 4 | Simple | Score drops to 3 |
| Function does more than one thing | Clear | Score drops to 3 |
| Cross-layer dependency introduced | Easy | Score drops to 3 |
| Public behavior without tests | Developed | Score drops to 3 |
| Commented-out code or unused imports | Brief | Score drops to 3 |

---

See also: [Evaluation Standards](eval_criteria.md) | [FIRST Scoring Rubric](FIRST_SCORING_RUBRIC.md)
