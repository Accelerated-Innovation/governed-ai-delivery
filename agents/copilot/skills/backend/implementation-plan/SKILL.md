---
name: govkit-implementation-plan
description: Generate an ordered implementation checklist with evaluation compliance summary from a validated preflight. Use when the user asks to draft implementation steps or invokes /govkit-implementation-plan.
---

# Implementation Plan

You are writing an evaluation-driven implementation plan for a feature. Determine the feature name from the user's request; if it is not provided, ask before proceeding.

## Behavior contract (skip unless this project has one)

Read `authority` in `.govkit/skill_context.yaml` before anything else. If
`source` is `none` — the default, and where most projects are — **skip this
section entirely**: nothing in it applies, and you should not mention it.

If `source` is `pdg`, this feature's behavior is a **versioned commitment**.
An approved baseline binds its Rules and scenarios to an exact revision, and
what somebody approved is that revision — not the working tree in front of
you, and not your reading of it. The governing rule is the one govkit
installed as `behavior-contract`; it is already loaded, and it is binding.

Before relying on anything in the feature folder:

- Run the `validate-baseline` and `verify-authority` checks exactly as that
  rule specifies them. Both need `--target` and `--baseline`, and
  `verify-authority` also needs `--commitment` — omit it and the answer is
  *not authorized* about the pointer you did not supply, which says nothing
  about your work.
- **Drift means stop.** The spec in front of you is not the one that was
  approved, and everything you plan from it inherits that.
- **Unverified is not permission.** An unreachable graph, or an unset
  `GOVKIT_PDG_URL`, leaves the question unanswered rather than answered yes.

Then change nothing that is committed. A scope change, an exclusion you
inferred, a behavior nobody asked for, or a relaxed threshold is a decision
for a person: name the scenario in conflict and wait. You may still refactor,
and this plan may still evolve, as long as every committed scenario keeps
passing.

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

## Inputs

Read these artifacts before planning:

- `features/<feature_name>/nfrs.md`
- `features/<feature_name>/acceptance.feature`
- `features/<feature_name>/eval_criteria.yaml`
- `features/<feature_name>/architecture_preflight.md`
- `docs/{{docs_area}}/evaluation/eval_criteria.md`
- `docs/{{docs_area}}/architecture/` (all files)

## Planning Requirements

The plan must:

- Follow **this project's architecture** — read `.govkit/skill_context.yaml`
  for `architecture.style` and the layer-to-folder mapping under
  `architecture.layers`. Cite `docs/{{docs_area}}/architecture/BOUNDARIES.md` for
  the canonical layer contract.
- Enforce FIRST principles for unit tests
- Enforce 7 Code Virtues for implementation
- Respect all boundary and dependency contracts
- Align with feature-specific eval thresholds

## Output Format

### Feature Summary

- Business goal, user value, success criteria

### Architecture Mapping

Map the work to the layers in `.govkit/skill_context.yaml` under
`architecture.layers` (inbound / outbound / domain). Cite the actual
folder names this project uses (per `skill_context.architecture.layers.*`
and `docs/{{docs_area}}/architecture/BOUNDARIES.md`). Explicitly confirm no
boundary violations.

### Task Breakdown (Ordered Checklist)

List all implementation steps in order. Each step must:

- Specify files/modules touched
- Reference the spec or architectural rule driving it
- Reference which FIRST principle it supports (if test-related)
- Reference which Code Virtue is at risk
- Mark with ADR required flag if applicable

### Test & Evaluation Plan

- How FIRST will be satisfied (mocking and isolation strategy)
- Simplicity and duplication risks
- LLM evaluation dimensions from `eval_criteria.yaml` and CI gate expectations

### Evaluation Compliance Summary

Predict before implementation begins:

- Expected FIRST average score (0–5) and justification
- Expected 7 Virtue average score (0–5) and justification
- Identified refactor triggers likely to occur
- Confirmation that `eval_criteria.yaml` thresholds are satisfied by design

If predicted averages are below required thresholds, adjust the plan before proceeding.

### Refactor Triggers

List conditions under which refactoring must occur:

- Duplication detected
- Complexity threshold exceeded
- FIRST or Virtue score below threshold

### Risks & Unknowns

Missing constraints, integration risks, performance concerns, security implications.

---

Do not generate implementation code. Plan must be executable as-is.
