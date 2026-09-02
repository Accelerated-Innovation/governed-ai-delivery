# Incremental Switchover

Read this reference before proposing a rewrite, broad API replacement, or transformation that cannot remain green in short steps.

The goal is a path from the current live system to the desired system in which each intermediate state is usable, testable, recoverable, and no worse by the evidence available.

## Switchover pattern

1. Introduce the new representation, API, or path beside the old one.
2. Preserve compatibility at their boundary.
3. Test that old and new agree where they should.
4. Move one caller, case, field group, route, or behavior.
5. Run the relevant feedback and keep the system usable.
6. Repeat in small authorized checkpoints.
7. Remove the old path only when callers and runtime evidence show zero use.
8. Remove compatibility scaffolding when it no longer protects a transition.

Examples include an old API delegating through a new representation, mirror execution with comparison, one endpoint or caller switching at a time, and a UI flow replacing one field group at a time.

## What “not worse” means

Treat “not worse” as an evidence-based constraint, not a claim of perfection. Consider:

- observable behavior and compatibility
- safety, privacy, and security
- performance and resource use
- operational visibility and rollback
- source clarity and temporary duplication

Temporary duplication can be legitimate transition scaffolding when ownership and removal conditions are explicit. Do not misapply SPOT to force a big-bang cutover.

## Avoid the rewrite trap

A parallel rewrite defers integration, behavior discovery, and user feedback while preserving the process that produced the current problems. Prefer changing live code frequently. If no incremental route is visible, report the obstacle and search for a smaller admission boundary rather than assuming a rewrite is authorized.

## Switchover plan

```text
Current live path:
Target path:
Compatibility mechanism:
Agreement check:
First caller/case to switch:
Verification after each switch:
Old-path removal condition:
Temporary duplication and owner:
Rollback or retreat point:
```
