# govkit vs GitHub Spec Kit — Positioning

> **Positioning source of truth.** How govkit (Governed AI Delivery) relates to, differs from, and is positioned against GitHub's Spec Kit. Generated 2026-06-04 from a review of the [Spec Kit repo](https://github.com/github/spec-kit) and its [spec template](https://github.com/github/spec-kit/blob/main/templates/spec-template.md). Use this doc to anchor sales, marketing, and product messaging.

## TL;DR

**Spec Kit generates specifications. govkit governs delivery.**

Spec Kit is a spec-*generation* workflow: a developer types a prose prompt, an AI agent drafts a spec/plan/tasks set, and the same operator implements it. govkit is a spec-*governance* system: structured, human-authored, collaboratively-refined specifications (real Gherkin + NFRs + evaluation criteria) are enforced against architecture contracts and blocking CI gates. They overlap in the middle — both own a per-feature artifact set and a repo-level "principles" document — but optimize for opposite ends: **velocity of generation** vs. **enforcement of correctness**.

The sharpest line: **Spec Kit makes specifications executable; govkit makes contracts enforceable.**

---

## What Spec Kit actually is

Three findings from the source that shape the positioning:

1. **Intended user is the developer driving an AI coding agent** — a single operator in the terminal (Claude Code, Copilot, Codex, 30+ agents) who owns the feature from `/speckit.specify` through `/speckit.implement`. There is no first-class role for a PM authoring in a separate tool, nor for a team collaboratively refining before build. It is a solo-operator, greenfield-first, spec-to-code pipeline.

2. **The specs are structured, but do not use real Gherkin.** The spec template is well-sectioned markdown (prioritized user stories, `FR-###` functional requirements, `SC-###` measurable success criteria, key entities, edge cases, `[NEEDS CLARIFICATION]` markers). Its "Acceptance Scenarios" are **Given/When/Then written as inline numbered prose** — not `.feature` files, not tagged (`@nfr-*`), not executable by any BDD runner. There is no structured NFR artifact (only prose "Success Criteria") and no evaluation-criteria concept at all.

3. **The driving prompt originates in the agent chat.** The human operator types `/speckit.specify <free-text>` and the agent drafts the structured spec from it (optionally tightened by `/speckit.clarify`'s Q&A). There is no upstream product tool; structure is *generated from* a prose prompt, not *authored*.

---

## The core distinction: Generate vs. Govern

| Dimension | GitHub Spec Kit | govkit (Governed AI Delivery) |
|---|---|---|
| **Core job** | Generate spec → plan → tasks → implement | Govern the agent against enforced contracts |
| **Intended user** | Developer driving a coding agent (solo operator) | PM drives the spec; QA + Eng refine; agent executes under gates |
| **Where the spec comes from** | Agent **drafts** it from a typed prose prompt | Humans **author** it (e.g. Aha!-generated first draft), team refines |
| **Acceptance format** | Given/When/Then as inline **prose** | **Real tagged Gherkin** (`.feature`, `@nfr-*`), BDD-runnable |
| **NFRs** | Prose "Success Criteria" only | Structured `nfrs.md`, thresholds + evidence + owner |
| **Evaluation criteria** | None | `eval_criteria.yaml`, schema-validated, thresholds |
| **Principles doc** | `constitution.md` — advisory, agent reads it | Architecture contracts + eval criteria — **enforced in CI** |
| **Clarify step** | `/speckit.clarify` — solo agent Q&A | `/govkit-clarify` — team 3-Amigos facilitation + Example Mapping over real artifacts |
| **Consistency / readiness check** | `/speckit.analyze` — advisory | `/govkit-spec-readiness` — **blocking** repo gate + Development Token |
| **Enforcement** | None mechanical | Import-linter (architecture boundaries), schema validation, eval-prediction thresholds, Sonar/Snyk |
| **Architecture stance** | Deliberately architecture-agnostic | Opinionated: hexagonal / MVVM / dbt-layered, boundaries enforced |
| **Quality model** | Qualitative checklists ("unit tests for English") | FIRST + 7 Virtues, scored 1–5 with ≥ 4.0 floor |
| **LLM-app governance** | None | L5 GenAI Ops: LiteLLM routing, DeepEval/Promptfoo/RAGAS, guardrails |
| **Agent support** | 30+ agents | 3 (Claude Code, Copilot, Codex) |
| **Posture** | Velocity, greenfield 0→1, research/experimental | Compliance, auditability, enforced delivery |

---

## The spec pipeline, compared

Spec Kit and govkit both run a front-to-back pipeline. The difference is **who drives**, **what the artifacts are**, and **whether anything is enforced**.

| Stage | Spec Kit | govkit |
|---|---|---|
| **Author** | Operator types `/speckit.specify` prose; agent drafts | PM drives a structured first draft (Aha! → Gherkin + NFRs + eval criteria) |
| **Clarify** | `/speckit.clarify` — agent asks the operator questions | `/govkit-clarify` — QA + Eng + Product refine together (3 Amigos, Example Mapping), producing an agreed Draft 1 |
| **Ready?** | `/speckit.analyze` — advisory consistency pass | `/govkit-spec-readiness` — strict repo gate: package completeness, repo-fit, agent-safety, **Development Token** (no token, no coding) |
| **Plan / Tasks** | `/speckit.plan`, `/speckit.tasks` | Architecture Preflight + Spec Planning + Implementation Plan skills |
| **Implement** | `/speckit.implement` | Agent executes Draft 1 under path-scoped rules |
| **Gate** | None | Blocking CI: architecture boundaries, eval thresholds, schema, Sonar/Snyk |

The two new govkit skills — **`/govkit-clarify`** (collaborative refinement) and **`/govkit-spec-readiness`** (repo readiness gate) — are the direct, and stronger, answers to Spec Kit's `/speckit.clarify` and `/speckit.analyze`:

- Spec Kit's clarify is a **solo agent Q&A**; govkit's is a **team facilitation** over *real, structured* artifacts, ending in an explicit go/no-go (`Development Token`).
- Spec Kit's analyze is an **advisory** consistency check; govkit's readiness is a **blocking gate** that also validates repo-fit and coding-agent safety before any code is written.

---

## Where each genuinely leads

**Spec Kit leads on generation and reach.** It drafts the spec for you, supports 30+ agents, integrates natively with GitHub (issues via `/speckit.taskstoissues`, PRs), and carries GitHub's distribution and brand. Its `constitution` + `/analyze` + `/checklist` are inching toward governance territory — worth watching. Do **not** try to out-compete it on agent breadth or greenfield turnkey-ness.

**govkit leads on enforcement, structure, and the human front-end.** Five things Spec Kit structurally cannot match without abandoning its flexibility thesis:

1. **Real, executable specs** — tagged Gherkin + structured NFRs + schema-validated eval criteria, not prose approximations.
2. **A human, collaborative spec front-end** — PM-driven authoring and team refinement (`/govkit-clarify`), versus a solo operator's prose prompt.
3. **Mechanical enforcement** — architecture-boundary linting and eval thresholds that actually block a merge, plus a `Development Token` readiness gate.
4. **Opinionated architecture** — hexagonal / MVVM / dbt-layered, enforced.
5. **GenAI operations** — governance for LLM-powered features (routing, eval, guardrails), which Spec Kit doesn't touch at all.

---

## Positioning statements (messaging)

Use these directly:

- **"Spec Kit generates specs. govkit governs delivery."**
- **"Spec Kit makes specifications executable. govkit makes contracts enforceable."**
- "Spec Kit drafts prose Given/When/Then. govkit runs real, tagged Gherkin your team refined together."
- "Spec Kit is a solo operator typing a prompt. govkit is a PM-driven spec, a team refinement, and a gate that says *no token, no coding*."
- "Spec Kit asserts quality with checklists. govkit gates it in CI."
- "For LLM-powered features, govkit is the only one of the two that governs routing, evaluation, and safety."

---

## Honest cautions

1. **They may be complementary, not strictly rival.** A team could use Spec Kit for greenfield spec generation and govkit as the enforcement layer beneath it. A "govkit hardens Spec Kit output" story may convert better than a pure "vs." — especially for teams already on Spec Kit.

2. **Spec Kit is the bigger competitive threat precisely because it's GitHub.** Its distribution, 30+ agent support, and creeping governance features (`constitution`, `/analyze`, `/checklist`) mean the gap could narrow. If Spec Kit ever ships *enforced* gates, govkit's remaining moat is architecture depth, the human/collaborative spec front-end, and GenAI operations. Lean into those now, and keep the two-skill pipeline (`/govkit-clarify` + `/govkit-spec-readiness`) visible as proof govkit owns the governed path end-to-end.

## Related

- Competitor comparison anchor: this document.
- `plans/HARNESS_GAP_ROADMAP.md` — the OpenAI Harness Engineering comparison (validation angle).
- In-progress skills: `/govkit-clarify` (collaborative refinement) and `/govkit-spec-readiness` (repo readiness gate).
- Sources: [github/spec-kit README](https://github.com/github/spec-kit), [spec-template.md](https://github.com/github/spec-kit/blob/main/templates/spec-template.md).
