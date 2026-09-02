---
name: user-pov-sliced-stories
description: Format thin vertical slices as explicit "User invokes" and "User uses result" outcomes. Use when the split already exists or the user specifically wants user-observable wording for slices. For choosing the split sequence itself, prefer `story-splitting-for-delivery` (progressive admission). Also use when reframing a technical plan into user-visible slices after admission planning is complete.
---

# User POV Sliced Stories

## Role of this skill
This skill is a **formatter**, not a splitter.
It translates an existing admission plan into user-visible invoke/result language.

Primary splitting — choosing the admission boundary, sequencing slices, writing Slice 0, bargain-hunting the next case — belongs in `story-splitting-for-delivery`.
Apply this skill after that plan exists, or when the user specifically asks for user-observable wording.

## Build slices as user-visible behavior
Define each slice as an end-to-end behavior a user can trigger and benefit from immediately.
Avoid component-only splits (UI-only, API-only, DB-only).
Each slice must be independently demoable.

## Workflow
1. If no admission plan exists yet, create one with `story-splitting-for-delivery` first.
2. Restate the capability in customer terms: who, behavior change, value now.
3. For each admission slice, write the user-visible invoke/result pair (see format below).
4. Keep slices small — typically 1–3 days.
5. Define concrete acceptance examples before implementation.
6. Re-split after each delivered slice based on feedback.

## Required output format
For each slice, always produce:

### Slice N — \<short user-facing title\>
- **User invokes:** \<exact command, UI action, API call, or trigger\>
- **User uses result:** \<observable value/output the user consumes immediately\>
- **Acceptance checks:** \<2–4 testable checks\>
- **Not yet in this slice:** \<explicitly deferred scope\>

## Sequencing rules
- Deliver 2–5 slices at a time.
- Put the safest value slice first.
- Put highest uncertainty reduction in slice 1 or 2.
- Keep later slices negotiable; do not over-specify implementation.

## Quality gate before finalizing slices
Confirm each slice:
- is demoable to a stakeholder
- provides value or learning even if work stops afterward
- is testable independently
- remains vertical and user-observable
- is small enough for fast feedback

## Response style
- Write from user POV, not component POV.
- Prefer concrete invocation language: command name, button label, menu path, API endpoint.
- Keep each slice concise and high signal.
- If the plan uses technical admission language, translate it — do not copy paste implementation details.

## Relationship to nearby skills
- `story-splitting-for-delivery`: primary splitter — defines admission boundary, Slice 0, and admission sequence.
- `user-pov-sliced-stories` (this skill): formatter — restates the output of that plan in user-visible language.

Invoke `story-splitting-for-delivery` when the question is "how do we cut this work?"
Invoke this skill when the question is "how do we describe these slices to stakeholders?"
