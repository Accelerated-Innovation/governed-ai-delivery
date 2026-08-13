---
name: govkit-fix-record
description: Author a fix record for a defect that restores already-established behavior. Use when the user reports a bug, asks to fix a defect, or invokes /govkit-fix-record.
---

# Fix Record

Author the fix record for a reported defect. When invoked, determine the defect from the user's request; if it is not described, ask before proceeding.

A defect that restores behavior something already established carries one record — `fixes/<id>/fix.yaml` — instead of the five-artifact feature contract. A change that introduces behavior does not qualify, however small it looks.

## Check eligibility first

All four conditions must hold. Decide this **before** writing any code or any record — a change that fails one belongs in the feature lane, and finding that out after the fix is written wastes the work.

1. **It restores established behavior.** Name the requirement, contract, ADR, or spec that established it. If nothing did, this is new behavior.
2. **A reproduction test is possible.** You will write a test that fails before the fix and passes after.
3. **It introduces no new intended behavior.** Fixing a defect by adding a capability is not a fix.
4. **It does not change** architecture, security or auth, data handling, a public contract, an NFR, or cross-service ownership.

If any condition fails, stop and say which one, then direct the user to `/govkit-architecture-preflight` and the feature lane. Do not author a fix record for a change that does not qualify — the lane is narrow on purpose, and widening it by assertion is the failure mode it exists to prevent.

## Inputs to read

Feature specs (to find what established the behavior):
- `features/<feature_name>/acceptance.feature`
- `features/<feature_name>/nfrs.md`

Architecture standards:
- `docs/{{docs_area}}/architecture/` (all files)
- `docs/{{docs_area}}/architecture/ADR/` — an accepted ADR is a valid source

Repository facts:
- `.govkit/skill_context.yaml` — read `architecture.layers` for the folder hints in this repo, and `architecture.source_root` / `architecture.services` for where source lives. Do not assume a folder shape; read the recorded one.

## Multi-service repos

Read `.govkit/skill_context.yaml` before planning. When it lists more than
one entry under `architecture.services`, this repo holds several services
and every path in your output has to land inside one of them:

```yaml
architecture:
  source_root: ''
  services:
    - name: billing
      root: src/billing
    - name: orders
      root: src/orders
```

1. Work out which service the feature belongs to. Take it from the request
   when it names one — by service name, or by a path under that service's
   `root`.
2. If the request names none, **ask which service to plan for** and list the
   names. Do not guess, and do not plan across all of them at once.
3. Prefix every file path in your output with that service's `root`. A task
   touching `services/pricing.py` in the `orders` service is
   `src/orders/services/pricing.py`.
4. Name the chosen service in the plan summary, so a reader knows which part
   of the repo the plan applies to.

When `architecture.services` is absent, the repo holds a single service.
Use `architecture.source_root` as the prefix instead — an empty value means
the layer folders sit at the repo root and paths need no prefix.

## Instructions

1. Reproduce the defect. Identify the smallest change that restores the established behavior.
2. Write the reproduction test **first**, and confirm it fails. Tests define the specification; a fix whose test never failed has not been shown to fix anything.
3. Run `govkit fix init <id>` to scaffold the record. Use a short slug naming the defect, not the fix.
4. Complete every field. `expectation.source` and `reproduction.test` must be real repo-relative paths — `govkit validate` resolves them, and an unresolvable source means condition 1 was asserted rather than met.
5. Set every `risk` flag honestly. A `true` is not a waiver; it moves the change to the feature lane. If you find yourself wanting to set one `false` to stay in the lane, that is the signal you are in the wrong lane.
6. Implement the fix. Confirm the reproduction test now passes and no other test broke.
7. Run `govkit validate --target .` and resolve anything it reports.

## Output

Write `fixes/<id>/fix.yaml` with:

- `summary` — the defect in the language of the affected behavior, not the language of the code
- `expectation.source` + `reference` — what established the behavior, and where in it
- `failure.observed` — what actually happens, and `reported_in` if there is a report
- `surface.paths` — the files the fix changes. Not the test; that is `reproduction.test`.
- `reproduction.test` + `scenario` — the test and the case within it
- `risk.*` — all six flags
- `introduces_new_behavior: false`

Two of these are declarations the tooling cannot verify: that the fix restores established behavior, and that it introduces none. `govkit validate` checks that the source path resolves, not that it says what you claim. State them precisely so a reviewer can check them quickly — that is what the record buys, and it is worth being straight about the limit rather than treating a green validate as proof.

Write the test before the fix, and the record before the implementation. No implementation code in this step beyond the failing test.
