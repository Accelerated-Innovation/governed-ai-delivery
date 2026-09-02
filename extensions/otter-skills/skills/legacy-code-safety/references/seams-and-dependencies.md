# Seams and Dependency Breaking

Read this reference when relevant code cannot enter a test harness or its important effects cannot be observed.

## Diagnose before editing

- **Sensing problem:** the code runs, but the test cannot observe a value, decision, or outgoing effect.
- **Separation problem:** the code cannot run safely or repeatably because a collaborator is slow, destructive, unavailable, global, or uncontrollable.

A dependency can create both problems. Name the immediate need so the production edit remains small.

## Seam model

A seam is a place where behavior can vary without editing the code at that place. Its **enabling point** is where the alternate behavior is selected.

Look for existing seams before creating one:

- function or constructor parameters
- interfaces, callbacks, and overridable object behavior
- dependency-injection registrations
- imports, modules, package resolution, or link configuration
- command, HTTP, messaging, and filesystem boundaries
- configuration or environment values already designed to vary behavior
- preprocessing or build configuration in languages where that is idiomatic

The test should exercise production code. Do not add `if testing` branches.

## Minimal dependency-breaking moves

Choose the smallest move natural to the language and codebase:

- parameterize a constructed dependency
- extract a small adapter around an external API
- expose a computed result rather than intercepting deep internals
- make time, randomness, or identity an explicit input
- replace a hard-coded call through an existing import or link seam
- split pure decision logic from an effectful shell
- subclass and override only when that is already a coherent local technique

Preserve behavior during the move. Run available tests or characterization before and after each structural step.

Avoid introducing a general architecture merely to test one path. A seam is successful when it unlocks trustworthy feedback with limited new knowledge and ownership.

## Test doubles

Use a double to control or observe a collaborator, not to reproduce its entire implementation.

- A fake supplies a lightweight working implementation.
- A stub supplies controlled answers.
- A spy records relevant calls or effects.
- A mock encodes an expected interaction.

Prefer observable results over incidental call sequences. Extensive mocking, deep stubbing, or duplicated collaborator logic signals that the chosen boundary may be wrong.

## Pinch points

When many effects or callers converge, a pinch point can protect a larger relevant area with fewer tests. Use it only when its output is stable and meaningful. A broad pinch-point test may be slower or less diagnostic, so complement it with focused tests as the design becomes accessible.

## Required seam note

For every production edit made only to gain testability, record:

```text
Obstacle:
Sensing or separation:
Seam:
Enabling point:
Why this is the smallest coherent move:
Behavior-preservation evidence:
```
