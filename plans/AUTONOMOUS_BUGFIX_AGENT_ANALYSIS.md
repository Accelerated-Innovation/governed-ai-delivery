# Autonomous Bug-Fix Agent — Feasibility Analysis

**Status:** Analysis only — no implementation planned
**Scope:** Target repos governed at L4; agent opens PR, human reviews and merges
**Date:** 2026-08-13

> **Question asked.** Can a bug-fix agent that invokes Claude Code headless (`-p`) work autonomously against a repo with govkit installed at L4 — diagnose, fix, and open a PR with no human intervention?

> **Answer.** Yes, but only by stepping outside govkit's lifecycle — and the current design has no way to tell the difference. The interesting risk is not that the agent gets blocked. It is that it doesn't.

---

## 1. govkit's enforcement has three layers, and only one is real

| Layer | What's there | Bearing on headless |
|---|---|---|
| **Harness** | **Nothing.** No `.claude/settings.json`, no hooks, no `permissions`, no output styles anywhere in the payload. | Nothing mechanically constrains the agent. Governance is not enforced by the runtime. |
| **Prose** | **79 blocking-phrase occurrences across 26 files** in `agents/claude-code/`, mirrored verbatim to codex and copilot. | This is what actually stops a `-p` run — and it fires *before any code is written*. |
| **CI** | Real gates, but **no human gate in any shipped template.** No `environment:`, no `workflow_dispatch:`, no `pull_request_review:`, no CODEOWNERS. | Orthogonal to the bug fix — see §3. |

Two structural facts that matter more than they look:

- **CI templates are not live on install.** `cli/install_common.py:394` copies them to `<target>/ci/github/*.yml`, not `.github/workflows/`. Per `ci/README.md`, a human must copy them and set `REPO_OWNER`. Whatever a given target repo enforces depends on what that team wired up.
- **`--dangerously-skip-permissions` does nothing for the gates that matter.** The blocking gates are not permission prompts; they are instructions to emit a request and halt. No CLI flag addresses them.

---

## 2. The four gates that will actually stop the run (L4 backend)

| # | Gate | Source | Self-clearable? |
|---|---|---|---|
| 1 | "If required inputs are missing, stop and ask." / "If alignment is unclear, stop and ask." | `agents/claude-code/claude-md/l4-backend-api.md:25`, `:190` | No. `:190` sits under *Output Expectations* — it applies to every output, not just planning. |
| 2 | "Implementation must not begin unless all five artifacts exist." | `agents/claude-code/claude-md/l4-backend-api.md:39`, and `agents/claude-code/rules/generic/spec-compliance.md:17`, which **applies to all files in the project** | Only by authoring the specs itself — see §4. |
| 3 | Repo-scope **HALT** | `agents/claude-code/rules/generic/repo-scope-backend.md:16` | No — and it has a payload bug (§6). |
| 4 | ADR must be **Accepted** before implementation | `agents/claude-code/claude-md/l4-backend-api.md:86` | **No. Hard stop.** Nothing in the payload lets a non-human set `Status: Accepted`; `docs/backend/architecture/ADR/TEMPLATE.md` §10 wants named Architect / Security / Product signatures. ADR triggers include *"a shared schema, API contract, event definition, or data model is introduced or modified"* — reachable on a real bug fix. |

Every skill also opens with *"if it is not provided, ask before proceeding"*, and in multi-service repos `agents/claude-code/skills/backend/spec-planning/SKILL.md:29` says **"ask which service to plan for … Do not guess."**

**There is no defect lane.** Zero occurrences of `bug|hotfix|defect|triage` as a workflow across the entire payload. `govkit init` accepts only `--starter {backend,cli,ui-react,ui-angular,ui-nextjs,data}`. The vocabulary is "feature" everywhere: *"This lifecycle applies to every feature."*

---

## 3. The asymmetry that makes it work anyway

A **code-only PR** — the fix plus a regression test, touching no `features/` directory — passes CI:

- `cli/validate.py:648` iterates *existing* feature dirs. Untouched features still pass, so `govkit validate` stays green.
- The `governance-artifacts` job in `ci/github/quality-gate.yml` only fails a feature that has `plan.md` but no `architecture_preflight.md`. Untouched features are fine.
- The L3 quality gate's commit-format regex already accepts `fix(scope): …`.

So **CI does not require a feature folder for a bug fix.** The entire blockage is agent-facing prose. That is the crack this use case fits through — but note what it means: the governance model's opinion about this PR is expressed only in text the agent may or may not obey, and nothing downstream can tell whether it did.

---

## 4. The real failure mode: self-certification, not stalling

With no human to answer, a capable agent will not stall — it will **self-serve**. It creates `features/bug_1234/` and authors all five artifacts itself. And **every L4 gate passes**, because every gate is a shape check on prose the agent just wrote:

- `check_plan_eval_prediction` (`cli/validate.py:281`) regex-scrapes `average: ([\d.]+)` from a YAML block the agent authored. Write `4.5`, pass. **The 4.0 quality floor is self-attestation, not measurement.**
- `check_nfrs_no_tbd` greps for `TBD`. The agent writes plausible NFRs, pass.
- `check_gherkin_nfr_coverage` cross-references NFR sections against `@nfr-*` tags — the agent controls both sides of the comparison.

`ci/README.md` is admirably candid about this: FIRST scores, Virtue scores, and accessibility are listed as **"prediction-only"** — the gate reads numbers the agent itself wrote.

The consequence when a human reviews the PR: that reviewer receives a three-line bug fix **plus five documents of AI-authored governance prose they must audit to know whether any of it is true**. Governance cost moves from the agent to the reviewer, and the artifacts' signal value goes to zero — a green `validate` means "the agent filled in the boxes," nothing more. That is strictly worse than shipping no artifacts at all.

**Worth sitting with:** govkit's own `extensions/skill-oriented-agent-architecture/docs/backend/architecture/AUTHORITY_AND_APPROVAL_CONTRACT.md:164-171` — the authority model it ships for customer-built agent systems — lists as *prohibited patterns*: **"Permission declarations inside prompt text"** and **"Treating chat acknowledgment … as approval."** That is an exact description of how govkit's own delivery governance works. The framework holds the systems its users build to a standard its own delivery layer does not meet. Closing that gap is the real product question behind the bug-fix agent.

---

## 5. What works today, if this ships now

Given L4 with a human merge gate, the viable path is deliberate and narrow:

1. **Constrain to the code-only path.** Fix plus regression test. No `features/` directory, ever. Frame the bug as remediating an *existing* feature's spec, not as new work.
2. **Override the prose gates explicitly and visibly** via `--append-system-prompt` — an auditable statement that this run is in defect-remediation mode and must not author feature artifacts. Do it in the open, not by hoping the model ignores its own rules.
3. **Make stalling a first-class success outcome.** This is the single most important decision. When the agent hits a gate it cannot clear (an ADR trigger, an ambiguous root cause), it must **exit non-zero naming the unmet gate** rather than inventing its way past it. Every gate in §2 is currently self-clearable by a sufficiently motivated model; the calling harness, not govkit, has to be what says no.
4. **Commit format:** `fix(scope): description`. The L3 gate validates format across **every commit in `origin/main..HEAD`**, not just the tip.
5. **If the target is `ui-nextjs`**, `govkit doctor` runs in CI and D016's static DB scan is unwaivable — it fails on any `.sql` file, any `db/` or `migrations/` directory, or any `DATABASE_URL`-style key including in `.env.example`.

---

## 6. Two payload defects found along the way (independent of autonomy)

- **Repo-scope false HALT.** `agents/claude-code/rules/generic/repo-scope-backend.md:16` tells the agent to look for a *checked box*, but every shipped starter and worked example writes ``**Scope:** `single-repo` `` with no checkbox anywhere. A literal-minded agent HALTs on a correctly-filled file — **with a human present.** This is a live bug today, not an autonomy concern. Mirrored in `repo-scope-ui.md:16` and the preflight skills.
- **Inconsistent plan-approval wording.** `agents/claude-code/claude-md/l4-ui-react.md:88` says *"Do not begin implementation until Phases 1–3 are complete and approved"*; `l4-ui-angular.md` and `l4-ui-nextjs.md` describe the same 5-phase workflow and silently omit the approval sentence.

---

## 7. Where this lands against existing plans

`plans/HARNESS_GAP_ROADMAP.md` Initiative 2 ("Runtime legibility for the agent") already scopes this exact use case. Its *Done when* reads:

> A govkit-governed project can hand the agent a reported bug and have it reproduce, fix, and validate against the running app — at minimum for the UI path — with evidence attached to the PR.

Marked P1, Large, unstarted. The bug-fix agent is the forcing function for it.

The gap that roadmap entry **does not** name, and that this analysis surfaces: **govkit has no delivery-side actor model.** "The Architect" and "the feature owner" appear throughout the payload as entities the agent must request things from, but neither is ever defined, and neither has any mechanism to signal approval that a machine could read. `governance/` contains schemas and templates only — no policy document, no roles file, no approval matrix — despite `l4-backend-api.md:16` instructing the agent to operate aligned to "governance rules under `governance/`".

Until an approval can be *represented*, "autonomous but governed" has nowhere to live. The agent's only options are to stall or to forge.

---

## Decisions — all three answered

### 1. Defect lane — **DECIDED and DELIVERED** (2026-08-13)

govkit owns a lightweight, risk-tiered fix contract. The bug-fix agent may stay
an external harness, but its workflow does not sit outside governance.

Shipped: `fixes/<id>/fix.yaml` against `governance/schemas/fix_record.schema.json`,
`govkit fix init`, eligibility checks in `cli/fixes.py`, the diff-aware
`ci/*/fix-lane-gate.yml`, and `/govkit-fix-record` across all three agents.
L4+; L3 keeps no artifact model.

The four eligibility conditions and what verifies each are in the README's
defect lifecycle. Two of them — "restores established behavior" and "introduces
no new behavior" — remain **declared**, which is decision 2's territory.

### 2. Machine-verifiable approval — **DECIDED, NOT BUILT**

Yes, but as an **approval attestation**, not a name typed into an ADR or a field
in `.govkit/marker.json`. The marker represents installation and calibration
state, is repo-global, and has no approval semantics; overloading it would be
wrong.

The representation must carry: subject identity and exact artifact digest or
commit SHA; decision and scope; approver identity and authorised role; policy
version and issuer; timestamp, expiry, conditions, evidence references; and
verifiable provider provenance or a signature. CI verifies issuer, role, subject
digest, and freshness. Any relevant change invalidates the approval, so
`Accepted` becomes a **derived state**, not editable source text.

MVP: an authenticated GitHub/Azure review by an authorised team against the
current head SHA is sufficient provenance. A signed offline attestation is a
later profile.

This is what govkit's own `AUTHORITY_AND_APPROVAL_CONTRACT.md` already demands
of the systems its users build — scoped, evidence-linked, identity-bound,
revocable — and explicitly forbids satisfying with prompt or chat text.

### 3. Measured evidence over predicted scores — **DECIDED, NOT BUILT**

Keep predictions as **planning forecasts**. Stop calling them quality gates and
stop using the 4.0 floor as the headline value proposition until it is measured.

Measure what has credible observable evidence: Working (acceptance and
regression tests pass), Fast (recorded test-duration thresholds), Repeatable
(reruns and flake detection), Isolated (independent or randomised-order
execution), Unique/Simple/Brief (duplication, complexity, coupling, scoped-size
thresholds), Accessibility (actual axe results, not `predicted_axe_violations`),
and architecture/security from existing boundary and scanner results.

Clear, Easy, Developed and Timely stay advisory unless scored by an independent,
identified evaluator with evidence — never by the authoring agent.

The precedent already exists in-repo: `docs/data/architecture/ADR/0001-data-features-skip-prediction-gate.md`
(Accepted) calls the self-predicted 4.0 average "ceremony" and replaces it with
deterministic CI outcomes. Backend and UI should follow it.

Partially landed already: `check_plan_eval_prediction` now cross-checks the
declared average against the scores beneath it and enforces the rubric's
"no individual score below 3", which was never checked. That closes a
sloppiness gap, **not** the self-attestation one — reconciling two numbers the
same agent authored is not measurement.

Target position: *govkit requires a planning forecast before implementation and
measured quality evidence before merge.* Restore "4.0 quality floor" as a
headline only once evaluations are commit-bound, independently produced,
calibrated, and enforce both the average and the individual-score floors.

---

## Verification for any follow-on work

- `./run_tests` (fast, ~20s), then `./full_test` for the e2e tier.
- `pytest -k parity` plus `tests/test_agent_skills.py` — any payload change must land across all three agents in lockstep.
- `.\scripts\smoke.ps1 -Agents claude-code -Levels 4 -Force` for a real apply-plus-validate sandbox.
- For the repo-scope bug specifically: a failing test first, asserting the preflight and rule text accept the ``**Scope:** `single-repo` `` form the starters actually ship.
