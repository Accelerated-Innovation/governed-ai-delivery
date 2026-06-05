# Harness Gap Roadmap — Closing the Distance to OpenAI's Agent-First Harness

> **Source of truth for this initiative.** Each issue and PR opened against the three gaps below must trace back to a section in this document. Generated 2026-06-04 from a comparison of govkit against OpenAI's ["Harness engineering: leveraging Codex in an agent-first world"](https://openai.com/index/harness-engineering/) (Feb 2026).

## Context

OpenAI's Harness Engineering post describes building and shipping an internal product with zero manually-written code over five months — agents write everything, humans steer. Read against govkit, the post is largely **independent validation**: their hard-won principles (repo as system of record, invariants over implementations, plans as first-class artifacts, agent legibility) are things govkit already ships as installable defaults.

Three capabilities they describe have **no govkit equivalent yet**. None is a weakness in what govkit does today — govkit governs the *code*; these extend governance to *drift*, the *running system*, and *velocity evidence*. This roadmap captures them as three initiatives, prioritized, so they can be promoted into issues and PRs without losing the rationale.

The framing matters for positioning: OpenAI explicitly warns their bespoke harness "should not be assumed to generalize without similar investment." govkit's job is to package the generalizable layer. Closing these three gaps moves govkit closer to being the portable version of what they built internally.

---

## Initiative 1 — Autonomous garbage collection ("govkit gardener")  ·  Priority: P1

### Problem
govkit defines the quality bar — FIRST principles and the 7 Code Virtues, scored 1–5 with a ≥ 4.0 floor — but **remediation of drift is entirely manual**. Agents replicate whatever patterns already exist in a repo, including uneven ones, so a governed repo still accumulates "AI slop" over time. Today nothing scans for it or pays it down.

### What OpenAI does
They encode opinionated "golden principles" into the repo and run a recurring set of background Codex tasks that scan for deviations, update quality grades, and open **targeted refactoring PRs** — most reviewable in under a minute and auto-merged. They frame technical debt as a high-interest loan: cheaper to pay down continuously than in painful bursts. Their team used to spend ~20% of every week (Fridays) cleaning up slop manually before this; it didn't scale.

### Proposed approach
A scheduled/agent-driven "gardener" that govkit installs and a team can run on a cadence (CI cron or local agent task):

- A `docs/<area>/GOLDEN_PRINCIPLES.md` contract — opinionated, mechanical rules (e.g. prefer shared utility packages over hand-rolled helpers; validate boundaries, don't probe data shapes "YOLO-style").
- A `/gardener` skill that scans the repo against FIRST / 7 Virtues + golden principles, updates a `docs/<area>/evaluation/QUALITY_SCORE.md` grade per domain/layer, and opens scoped refactoring PRs.
- A CI workflow (`ci/github/gardener.yml` / Azure equivalent) to run it on a schedule and label/auto-merge low-risk fixes.
- Golden-principles are authored **per type** (backend, ui, data, cv...). The gardener is also the right home for **heavyweight, out-of-inner-loop audits** — e.g. perceptual-hash train/test leakage scans and per-slice eval regressions for ML types — that are too slow to gate on every commit but compound if unwatched.

### Rough sizing
Medium. Reuses the existing FIRST / 7 Virtues rubrics and quality-grade concept; the new surface is the scanning skill, the golden-principles contract, and the scheduled CI job. Land in two PRs (contract + skill, then CI wiring).

### Tracking
- [ ] Draft `GOLDEN_PRINCIPLES.md` contract (backend + ui variants)
- [ ] Add `QUALITY_SCORE.md` quality-grade artifact + schema
- [ ] Build `/gardener` skill (scan → grade → scoped refactor PRs)
- [ ] Add scheduled CI workflow with auto-merge for low-risk fixes
- [ ] Document the cadence + review expectations in README

### Done when
A govkit-governed repo can run the gardener on a schedule, see per-domain quality grades update over time, and receive small auto-mergeable refactoring PRs without manual slop cleanup.

---

## Initiative 2 — Runtime legibility for the agent  ·  Priority: P1

### Problem
govkit makes the **code** legible to the agent (architecture contracts, path-scoped rules, specs). It does **not** make the **running system** legible. The agent governs what it can read statically, but cannot reproduce a bug, drive the app, or reason over live logs/metrics/traces. This is arguably the single biggest capability gap versus the OpenAI harness.

### What OpenAI does
They invested heavily in making the running app legible to Codex: the app is **bootable per git worktree** (one isolated instance per change); Chrome DevTools Protocol is wired into the agent runtime with skills for DOM snapshots, screenshots, and navigation; and a per-worktree ephemeral observability stack exposes logs (LogQL), metrics (PromQL), and traces (TraceQL). This lets prompts like "no span in these four critical journeys exceeds two seconds" become tractable, and lets the agent reproduce a bug, fix it, and validate the fix by driving the app — recording before/after videos.

### Proposed approach
This is the heaviest item and is best staged. govkit can't ship a universal runtime harness, but it can ship the **governed contract + skills** that standardize one:

- A `docs/<area>/RUNTIME_LEGIBILITY_CONTRACT.md` defining what a govkit-governed project must expose to the agent (per-worktree boot, structured logs the agent can query, a metrics/trace endpoint).
- A `/drive-app` skill family: boot the app for the current worktree, drive a UI path (DevTools/Playwright), capture before/after evidence, tear down.
- An observability convention (structured logging is already a govkit taste invariant) extended to a queryable local stack the agent can read.
- **Model/eval-artifact legibility (ML + data types):** for non-UI systems, "runtime" is the evaluation run. The agent should be able to read a structured metrics+provenance artifact (per-class/per-slice metrics, eval protocol, dataset version) and visual failure evidence (confusion matrix, failure-case montage) and iterate on the model. This is the ML analogue of driving the UI — CV is the forcing function; the `data` type benefits identically.
- Stage 1 = contract + UI driving evidence; Stage 2 = log/metric/trace querying.

### Rough sizing
Large; stage it. Stage 1 (contract + UI driving + evidence capture) is a self-contained deliverable. Stage 2 (observability querying) depends on a reference stack and is a follow-on.

### Tracking
- [ ] Draft `RUNTIME_LEGIBILITY_CONTRACT.md` (what a project must expose)
- [ ] Build `/drive-app` skill: per-worktree boot + UI drive + before/after evidence
- [ ] Define structured-logging + local observability convention for agent querying
- [ ] Stage 2: log/metric/trace query skills (LogQL/PromQL/TraceQL-equivalent)
- [ ] Reference example wiring in `extensions/` or a sample repo

### Done when
A govkit-governed project can hand the agent a reported bug and have it reproduce, fix, and validate against the running app — at minimum for the UI path — with evidence attached to the PR.

---

## Initiative 3 — Throughput as a first-class metric  ·  Priority: P2

### Problem
govkit's framing is compliance-first. There is no instrumentation that shows governance **doesn't** tank velocity — which is the first objection a throughput-focused engineering leader will raise. We assert quality; we don't yet measure delivered pace inside the governed system.

### What OpenAI does
They treat human time and attention as the one scarce resource and measure throughput directly — PRs per engineer per day (3.5, and *increasing* as the team grew) — using it as the calculus for nearly every tradeoff (relaxed merge gates, agent-to-agent review, continuous GC).

### Proposed approach
Lighter than the other two, and high marketing/positioning value:

- A `govkit metrics` command (or CI summary) that reports governed-delivery throughput: features/week through the L4 contract, CI gate pass rates, time-in-gate, gardener PRs merged.
- A definition of "governed throughput" as the headline metric — pace *with* enforced gates, not raw PR count.
- An optional dashboard artifact for teams to track it over time.

### Rough sizing
Small–medium. Mostly aggregation over existing `.govkit` markers, feature artifacts, and CI history.

### Tracking
- [ ] Define the "governed throughput" metric set
- [ ] Add `govkit metrics` aggregation over `.govkit` + features + CI history
- [ ] Optional: live dashboard artifact
- [ ] Use the numbers in external positioning (governance ≠ slower)

### Done when
A govkit team can produce a credible governed-throughput number and trend, suitable for both internal review and external positioning.

---

## Prioritization summary

| Initiative | Priority | Sizing | Why this order |
|---|---|---|---|
| 1 — Gardener | P1 | Medium | Highest leverage; reuses existing FIRST / 7 Virtues + quality-grade machinery. Closes a gap that actively compounds. |
| 2 — Runtime legibility | P1 | Large (stage it) | Biggest capability gap, but heavy. Stage 1 (UI driving) ships independently; stage 2 follows. |
| 3 — Throughput metrics | P2 | Small–medium | Lightest; strongest positioning payoff. Good fast-follow once 1 is moving. |

## Related

- Email to CTO summarizing the comparison: `govkit_vs_harness_email.docx` (repo root).
- Source: OpenAI, ["Harness engineering: leveraging Codex in an agent-first world"](https://openai.com/index/harness-engineering/), Feb 2026.
- Existing quality framework: FIRST principles + 7 Code Virtues (see README, `docs/<area>/evaluation/`).
