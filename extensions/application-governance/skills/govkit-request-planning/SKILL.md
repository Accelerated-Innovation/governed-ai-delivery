---
name: govkit-request-planning
description: Normalize a request and select proportional work from accepted policy.
---

# Request planning

1. Run `govkit request template` to obtain a proposed local record. Preserve the owner's original request reference and summarize the agreed intent and acceptance locally. Ask only about missing facts that affect the decision. Inspect relevant accepted contracts, NFRs, tests, and affected paths; keep unknown impact values `null` until resolved. Agent guesses remain proposed. Never equate a small diff or a ticket label with low impact.
2. Capture literal repository-relative scope and all impact assertions. Reference existing local acceptance/NFR/contract sources instead of copying them. A defect must restore accepted established behavior with an existing local regression test and retain the existing fix-record eligibility and red/green evidence. New bounded behavior may use a compact change record. Confirm intent with the owner before changing `confirmation` to `confirmed`; that field records an assertion, not independent approval.
3. Run `govkit request plan request.json --target .`. Inspect decisions and follow only guidance named by the verified pinned plan. Use `--explain` or `--json` for requirements and provenance. Missing capabilities require an explicit profile/pack preview and authorized installation; do not download packs, waive checks, change policy, or reconfigure the repository automatically.
4. Save the normalized request and generated plan through the project's reviewed change process. The plan lists obligations, not passed checks. For bounded work keep intent, acceptance, reused references, scope and decisions together, with actual test evidence. Full-feature work uses the spec/plan/preflight/test-plan/validation artifacts. LLM evaluation is independent of Gherkin delivery. Architecture changes need accepted current/target rules, approval and transition verification; never accept an ADR on the owner's behalf.
5. Re-plan whenever intent, policy, references, resources or scope changes. Supply `--previous plan.json` and optionally `--scope observed-scope.json`; scope observations may add risk, never erase required controls. This planner does not derive a Git diff or enforce CI conformance. Keep authentication, security, data, public-contract, NFR, ownership and architecture controls regardless of the preferred workflow.

Planning is offline and read-only. The CLI prints to stdout; saving a file is an explicit caller action. No live tracker lookup or tracker writes are required.
