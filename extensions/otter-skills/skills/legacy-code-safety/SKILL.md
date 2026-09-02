---
name: legacy-code-safety
description: >
  Establish trustworthy feedback around poorly understood or weakly tested
  existing code before changing it. Use for characterization or approval tests,
  test-harness access, seams, sensing and separation, dependency breaking, and
  incremental replacement of risky live code. Once a fast trustworthy boundary
  exists, use unit-testing to drive the requested new behavior.
---

# Legacy Code Safety

Make one requested change safe without demanding a cleanup campaign or rewrite first.

Legacy code is code for which the relevant behavior cannot be verified quickly and reliably. Existing tests may be absent, slow, flaky, too broad, or coupled to irrelevant structure. The immediate job is to establish enough trustworthy feedback for the change at hand.

## Ownership and boundaries

Use this skill when:

- relevant behavior is undocumented, surprising, or poorly understood
- existing tests do not protect the intended change
- dependencies or side effects keep code out of a test harness
- the task calls for characterization, pinning, approval tests, seams, sensing, separation, or safe legacy-code change
- a large brownfield transformation needs an incremental path through live code

Do not use it as the primary skill when:

- a fast trustworthy test boundary already exists; use `unit-testing`
- the request is review-only; use `representation-refactor-review`
- the task is only to choose delivery slices; use `story-splitting-for-delivery`
- the user requested a wholesale replacement; do not silently turn this skill into authorization for one

This skill owns **establishing safety**. `unit-testing` owns specifying and implementing the new behavior after that boundary exists.

## Safety invariants

- Start from an intentional workspace and record relevant inherited failures before editing.
- Characterization describes observed behavior, not desired behavior.
- Separate observations, suspected defects, and requested changes.
- Break only the dependencies that block sensing or separation for this change.
- Production code must not branch on whether it is under test.
- A test is not a safety net until it has demonstrated that it can fail for a relevant change.
- Prefer small, reversible changes through live code over a parallel rewrite.
- Preserve unrelated user work. Create commits or external changes only when authorized.

## Workflow

### 1. Frame the change and risk

Before editing, state:

```text
Requested change:
Likely change point:
Relevant entry-to-exit path:
Behavior that must remain stable:
Dangerous or unavailable dependencies:
Current feedback and inherited failures:
```

Ask three questions throughout: How will we know the requested change is correct? How will we know relevant existing behavior remains intact? How cheaply can we recover from a wrong step?

### 2. Find the narrowest useful test point

Prefer the cheapest boundary that protects the requested change:

1. an existing focused public behavior
2. an existing seam near the change point
3. stable subsystem output suitable for approval testing
4. a pinch point through which several relevant effects pass
5. a minimal new seam

Do not default to a full end-to-end harness or mock every collaborator. Read [references/seams-and-dependencies.md](references/seams-and-dependencies.md) when code cannot run or relevant effects cannot be observed.

### 3. Characterize relevant behavior

For one concrete input, run the current code and capture what it actually does. Establish that the test initially fails or that output is initially unapproved, inspect the observation, then record it with a behavioral name.

Add cases for relevant branches, boundaries, failure paths, and known production examples—not indiscriminate coverage. Record suspected defects separately; do not fix or bless them silently.

Use ordinary assertions for small focused results. Use approval testing for large structured output that is easier to review as a diff. Read [references/characterization-and-approvals.md](references/characterization-and-approvals.md) before creating approval artifacts.

### 4. Prove the safety net

Demonstrate at least one relevant failure by seeing the initial expectation fail, making and reverting a deliberate perturbation, or using a focused mutation. Coverage identifies unexercised code; it does not prove that assertions detect change.

Restore the baseline immediately after any deliberate perturbation.

### 5. Introduce only necessary seams

For each blocking dependency, identify:

```text
Obstacle:
Need: sensing | separation
Seam and enabling point:
Smallest production edit:
Evidence behavior is preserved:
```

Keep preparatory edits structural and green. Prefer explicit parameters or small adapters when natural in the codebase, but use language and build-system seams when they are safer than broad redesign.

### 6. Hand new behavior to TDD

Once the boundary is fast, reliable, and capable of detecting relevant change, use `unit-testing`:

1. write one failing test for the requested behavior
2. make the minimum production change
3. refactor while green
4. retain characterization tests until focused tests safely supersede them

Do not confuse a characterization expectation with a test-first specification.

### 7. Switch incrementally when the change is large

If the transformation cannot finish in a short safe cycle, keep old and new paths able to coexist, prove compatibility, and move one caller, case, or route at a time. Remove the old path only when evidence shows it is unused.

Read [references/incremental-switchover.md](references/incremental-switchover.md) before a parallel implementation, broad API change, or rewrite proposal.

### 8. Finish with evidence

Report:

```text
Requested change:
Observed legacy behavior:
Characterization added:
Seams used or introduced:
Safety-net failure demonstrated:
New behavior test and implementation:
Verification:
Temporary scaffolding:
Remaining unprotected risks:
```

## Stop and report rather than guess

Stop or narrow the work when characterization would:

- execute destructive production effects
- capture secrets, personal data, or environment-specific credentials
- approve output nobody has inspected
- depend on uncontrolled nondeterminism that obscures meaningful changes
- require a public-contract change beyond the user's authorization
- discard or overwrite unrelated work to regain a baseline

When a unit remains unreachable, report the smallest seam that would unlock it and the risk of that edit. Do not fabricate confidence.

## Related skills

- `unit-testing` — owns test-first implementation after a trustworthy boundary exists.
- `representation-refactor-review` — owns broad representation critique; this skill changes only enough representation to make the requested work safe.
- `story-splitting-for-delivery` — owns delivery-slice selection. Use incremental switchover here to execute a chosen brownfield slice safely.
- `code-object-naming` — owns focused naming analysis; routine names introduced by a seam should simply match the local dialect.

For source attribution and further reading, see [references/sources.md](references/sources.md).
