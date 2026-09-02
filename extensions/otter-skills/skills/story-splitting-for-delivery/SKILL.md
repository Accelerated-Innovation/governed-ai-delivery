---
name: story-splitting-for-delivery
description: >
  Split oversized features, epics, and stories into thin, demonstrable,
  deployable slices
  through progressive admission: start with a closed end-to-end skeleton, then
  admit one case at a time. Use to choose or sequence delivery slices, including
  message, schema, import, API, form, path, rule, persona, or channel rollouts.
  Do not use merely to format an already-chosen split as user-visible outcomes;
  that belongs to user-pov-sliced-stories.
---

# Story Splitting for Delivery (Progressive Admission)

## Core idea
This is the primary story-splitting skill.
Build the end-to-end path first, fully closed. Then admit one safe case at a time.
Everything not yet admitted stays rejected — invalid, unsupported, or not implemented.
Each admission is a thin, testable, demonstrable, ideally deployable story.

This is related to walking skeleton / tracer bullet thinking, but the distinctive move is **default-deny with progressive widening**.

## When this skill fits
Use it as the default whenever work is too big for one iteration or needs a delivery sequence.
Progressive admission is especially natural when there is a clear cycle:
- message queue / event processing
- HTTP operations or API handlers
- batch file / import processing
- form fields and validation
- UI controls that enable one action after another
- schema or protocol versioning over time
- multi-path user journeys, roles, channels, or rule variants

If the admission boundary is not obvious, invent one from the variations in the work (paths, data shapes, rules, interfaces, roles). Do not fall back to component/task decomposition.
Use `user-pov-sliced-stories` only when the main need is user-invoke / user-uses-result formatting.

## Target shape of each admission slice
A good admission slice:
- keeps the full end-to-end path wired
- admits exactly one new case, shape, type, field set, or rule
- continues to reject all non-admitted cases with a stable response
- is unit-testable and end-to-end testable
- produces an observable result that can be demonstrated without later admissions
- could be deployed without harming unhandled traffic
- leaves room to TDD and refactor after green

## Progressive admission workflow

### 1) Name the admission boundary
State what is being admitted:
- message type / event type
- request shape
- file format or row shape
- UI action / command
- business rule variant
- schema version

Also name the default rejection:
- not implemented
- invalid input
- unsupported operation
- unknown type

### 2) Start closed (Slice 0)
Build the end-to-end skeleton that correctly does nothing useful yet:
- reader/entry point exists
- checker/guard exists
- processor path exists but is not entered for real work
- every input is rejected by the established pattern

Value of Slice 0:
- clients can integrate against rejection behavior
- exception handling and reporting can be tested
- deploy path and observability can be proven early

### 3) First admissions (often non-business)
Admit the simplest useful closed-world cases first:
- health / ping / noop
- deliberately ill-formed input rejected with a specific error
- auth/identity failure if that is the front door

These prove the admit/reject machinery before real business logic lands.

### 4) Admit one real case
Choose one case using bargain hunting:
- simplest shape, or
- most common shape, or
- highest learning / risk-reduction shape

Implement only that admitted case. All other cases remain rejected.

### 5) Widen one admission at a time
Each later slice admits exactly one more:
- another message type
- another field combination
- another path branch
- another rule
- another output variation

Do not bundle "the rest of the cases" into one catch-up story unless they are truly trivial and still independently testable.

### 6) Finish planned admissions, keep the reject path
When planned cases are done:
- surprise inputs still hit the established reject path
- the service may already be in production doing useful work
- remaining edge cases stay optional backlog, not a launch blocker

### 7) Continue admissions over the life of the system
New messages, fields, schemas, and rules keep using the same pattern:
admit one, test thoroughly, deploy, repeat.

## Versioning guidance
When interfaces are versioned:
- adding a new admitted message/shape: minor bump
- changing or removing an existing admitted contract: major bump
- only changes to already-shipped contracts are breaking

## Required output format
Produce a short admission plan, not a component task list.

```markdown
# Progressive admission plan: <capability>

## Admission boundary
- **Admits:** <what varies: messages, shapes, ops, fields, rules>
- **Default reject:** <stable not-implemented / invalid response>
- **End-to-end path:** <entry -> guard -> process -> result>

## Slice 0 — Start closed
- **Admits:** nothing useful
- **Behavior:** every input rejected by the established pattern
- **Someone invokes:** <how a client, user, or stakeholder exercises the closed path>
- **Observable result:** <stable rejection, error, status, or diagnostic they can see>
- **Independent demonstration:** <how to show this result without later slices>
- **User/stakeholder value:** clients, errors, deploy path, and tests work end to end
- **Acceptance checks:**
  - <check>
  - <check>
- **Still rejected:** everything

## Slice 1 — <first admission title>
- **Admits:** <exact case>
- **Behavior:** <what happens for that case only>
- **Someone invokes:** <the action, request, message, or input that exercises this case>
- **Observable result:** <what the invoker can see or use>
- **Independent demonstration:** <how to show this result without later admissions>
- **User/stakeholder value:** <why this admission matters now>
- **Acceptance checks:**
  - admitted case works
  - non-admitted cases still reject stably
- **Still rejected:** <explicit remainder>

## Slice 2 — <next admission title>
...
```

For each slice after 0, keep both sides explicit:
1. what is newly admitted
2. what remains rejected

## Sequencing heuristics
Prefer this order when unsure:
1. closed skeleton
2. reject/health/guard behavior
3. simplest valid admission (often hard-coded or minimal implementation)
4. most common real case
5. high-risk or high-learning variants
6. polish, performance, and broad edge coverage

Bargain-hunt each next admission:
- high learning or value per unit effort
- safe to deploy
- easy to test in isolation from later admissions

## Quality gate before accepting a slice
Ask:
- Is the end-to-end path still intact?
- Does this admit only one new case?
- Are non-admitted cases still rejected the same way?
- Can someone invoke this slice and observe a meaningful result?
- Can we demonstrate and deploy it without waiting for later admissions?
- Is it clear why this result is worth admitting now?
- Are unit and end-to-end checks obvious?
- If we stopped after this slice, would the system remain coherent?

If a proposed slice secretly requires many shapes, rules, or channels at once, split again.

## Anti-patterns
- Building all processors first, then wiring the entry point last
- "Support all message types" as a single story
- Horizontal splits: schema story → service story → UI story
- Opening the guard to "pass everything" before implementations exist
- Treating reject/not-implemented as temporary junk instead of a productized path
- Over-specifying later admissions before slice 0 and slice 1 teach anything
- Calling component tasks "admissions"

## Facilitation script (20–30 minutes)
1. **3 min**: Name capability, users/clients, and the input-process-output cycle.
2. **5 min**: Define admission boundary and default reject behavior.
3. **5 min**: Write slice 0 (start closed) and its checks.
4. **7 min**: List candidate admissions; pick first 2–4 by simplicity/value/risk.
5. **5 min**: Write exact admitted case + still-rejected remainder for the next slice only.
6. **Optional 5 min**: Note versioning implications if contracts are external.

## Worked micro-example
Capability: process queue messages for account updates.

1. **Start closed**: consume message, validate envelope, always respond `not_implemented`.
2. **Admit ill-formed envelope**: reject with `invalid_message` and structured error.
3. **Admit health ping**: hard-coded `ok` result.
4. **Admit `AccountOpened` minimal shape**: create account with required fields only.
5. **Admit optional display name on `AccountOpened`**.
6. **Admit `AccountClosed`**.
7. Keep unknown types on `not_implemented`.

Demonstrate each step by submitting the newly admitted message and showing its
observable response, then submitting an unadmitted message and showing that the
stable rejection still holds. Each step is independently demonstrable,
testable, and potentially releasable.

## Relationship to nearby skills
- `story-splitting-for-delivery` (this skill): primary splitter; progressive admission sequence.
- `user-pov-sliced-stories`: optional formatter — restate each admission slice in user-invoke / user-uses-result language after the plan exists.

After building the admission plan, optionally apply `user-pov-sliced-stories` to restate slices in user-POV format.

## Sources
- Agile Otter: Progressive Admission Pattern
  https://agileotter.blogspot.com/2026/08/progressive-admission-pattern-for-data.html
- Agile Otter: Splitting Stories resource list
  https://agileotter.blogspot.com/2022/03/splitting-stories-resource-list.html
- Related ideas: walking skeleton, tracer bullets, evolutionary design / primitive whole, bargain hunting, scatter-gather avoidance, whole stories, example-based splitting.

For deeper pointers see `references/source-map.md`.
