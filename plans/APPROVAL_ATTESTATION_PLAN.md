# Approval Attestation Plan (Decision 2)

**Status:** Approved, not started
**Scope:** Make an ADR's `Accepted` status a derived state rather than typed text
**Date:** 2026-08-13
**Branch:** none yet — start from `main` at `89195a7`

> The third and last of the three decisions recorded in
> `plans/AUTONOMOUS_BUGFIX_AGENT_ANALYSIS.md`. Decision 1 (defect lane) shipped in
> #134; decision 3 (measured evidence) in #135, corrected by #136.

---

## Context

`Accepted` is a word someone types into a markdown file. The L4 rules gate on it
— *"ADRs … must be Accepted before implementation proceeds"* — and **nothing in
`cli/` or `ci/` has ever read it**. The templates' `## Status` and `## Approval`
sections sit ~140 lines apart, unlinked, and Approval is three empty
colon-terminated labels bound to no identity, no date, no commit.

govkit forbids exactly this, in a contract it ships to govern the agent systems
its *users* build. `AUTHORITY_AND_APPROVAL_CONTRACT.md` lists among **prohibited
patterns**: *"Permission declarations inside prompt text"*, *"Approval by an
unauthorized identity"*, *"Treating chat acknowledgment, elicitation, or
authentication as approval"* — and requires an approval be scoped, identity-bound,
time-bounded, revocable and evidence-linked. The delivery layer meets none of it.

**Goal:** `Accepted` becomes a **derived state** — true because an authorised
approver approved *this decision* at *this commit*, not because the word is there.

This is also the gate that started the whole thread.
`AUTONOMOUS_BUGFIX_AGENT_ANALYSIS.md` §2 lists ADR-must-be-Accepted as the only
*"No. Hard stop."* for an autonomous agent, precisely because nothing lets a
non-human set it. After this, nothing lets a *human* set it by typing either.

## Decisions taken

| Decision | Choice |
|---|---|
| Verification | **govkit verifies, platform enforces.** The gate binds an approval to a specific ADR and head SHA — which branch protection cannot do, since it approves a PR, not a document. govkit documents the CODEOWNERS + required-review setup it assumes underneath. |
| Migration | **Warn on pre-existing, fail on changed.** |
| Identity | **Approver logins in `governance/approval_policy.yaml`.** Verifiable with the default repo-scoped `GITHUB_TOKEN`; team slugs need `read:org` and a PAT. |

## The distinction that must not be collapsed

The authority contract separates two roles and states the rule plainly:

> | Reviewer | Assesses evidence or content |
> | Approver | Commits a scoped consequential decision |
>
> **A reviewer does not gain approval authority.**

So "an authenticated GitHub review is sufficient provenance" is only true once a
policy says *this identity holds the Approver role*. Without that mapping the
design collapses a distinction its own contract requires, and lands on the
prohibited pattern *"approval by an unauthorized identity"*.

The policy file is what turns a review into an approval. It is not bureaucracy
bolted on — it is the mechanism.

## The finding that makes migration non-negotiable

**govkit ships exactly one real ADR, and it would fail its own new rule.**

`docs/data/architecture/ADR/0001-data-features-skip-prediction-gate.md` says
`Accepted`, has **no Approval section at all**, and ships to every
`--type data` install at **L3, L4 and L5** — declared at the *type* level, as a
governed file `upgrade` rewrites. A check requiring an Approval block would fail
govkit's own shipped ADR in every data customer's repo on the next upgrade.

That is the exact defect class PR #133 existed to fix, so the migration posture
is not politeness — it is the difference between shipping and shipping a
regression.

It also forces a distinction worth making explicit: **ADR-0001 is *govkit's*
decision, not the customer's.** Requiring a customer's approver to attest a
decision govkit made for them is incoherent. The existing edit-protection
machinery already tells the two apart — `cli/headers.py` writes a
`<!-- govkit:editable -->` header carrying a body hash, so a govkit-authored,
unmodified ADR is identifiable without inventing a new mechanism.

## Two ADR vocabularies already ship

The templates emit `## 10. Approval` (UI numbers it `## 11.`). The `adr-author`
skill teaches `## Review` instead. Both ship from govkit, so a customer's ADR may
carry either. Any parser must tolerate both **and** the numbered prefix —
`cli/validate.py`'s existing `_populated()` helper (a closure inside
`check_nfrs_sections`, ~line 190) matches `^##\s+<name>` exactly and will **not**
match `## 10. Approval` without widening to `^##\s+(?:\d+\.\s*)?Approval\b`.

## Where the work splits

Same split as the fix lane, for the same reason: a working-tree tool cannot see
what only CI can.

| | `govkit validate` | `ci/*/adr-approval-gate.yml` |
|---|---|---|
| Sees | the working tree | the diff and the reviews API |
| Proves | the policy is well-formed and resolvable; which ADRs claim Accepted without provenance | an authorised approver approved **this ADR** at **this head SHA** |

**No new command.** Policy checks fold into `run_validation` beside
`_run_extension_checks` and `_run_fix_checks` — the established shape for a
second artifact family, and the CLI should not grow a command whose only real
answer lives in CI.

---

## Implementation sequence

TDD throughout; failing test first per increment; separate commits.

**1 — Policy schema.** `governance/schemas/approval_policy.schema.json`,
area-agnostic like `fix_record.schema.json`: draft 2020-12,
`$id: urn:governed-ai-delivery:schemas:approval_policy`,
`additionalProperties: false` everywhere, **`version` as an integer** (house
convention — a test rejects a string). Approvers carry `login` and `role`, with
`role` constrained to the authority contract's vocabulary so the Reviewer /
Approver distinction lives in the data, not just the prose. Tests mirror
`TestFixRecordSchema` in `tests/test_schemas.py`.

**2 — `governance/approval_policy.yaml`.** Shipped with a `YOUR_APPROVER_LOGIN`
sentinel, mirroring `repo-scope-check`'s `REPO_OWNER` and the fix-lane gate's
`SOURCE_PATHS`. Inert until edited, so a fresh install stays green. It also makes
true, for the first time, `l4-backend-api.md:16`'s instruction to follow
*"governance rules under `governance/`"* — a directory that has only ever held
schemas and templates.

**3 — `cli/approval.py`.** Modelled on `cli/fixes.py`: own module,
`(issues, warnings)` ABI, silent when absent. Discovers ADRs excluding
`TEMPLATE.md`, parses `## Status` (reuse the regex already in
`tests/test_adr_contract_consistency.py:52-56`), loads and validates the policy.
Emits **warnings, not issues**, for a customer-authored ADR claiming `Accepted`
without provenance; **silent** for a govkit-authored unmodified one.

**4 — Wire into `validate`** — `_run_approval_checks(target)`, combined via `max()`.

**5 — `ci/{github,azure}/adr-approval-gate.yml`.** Job `adr-approval-check`
(verified free against `tests/test_ci_gate_composition.py`).
`permissions: pull-requests: read` — **a first for the payload**, which declares
no `permissions:` block anywhere today. `fetch-depth: 0` and
`git diff --name-only origin/main...HEAD -- 'docs/*/architecture/ADR/*.md'`
(three-dot, the merge-base form), excluding templates. For each changed ADR
claiming `Accepted`, require an approving review whose `commit_id` is the head
SHA and whose `user.login` is an Approver in the policy. Pins `govkit~=<version>`
if it invokes the CLI — `tests/test_ci_govkit_dependency.py` now auto-enrols any
subcommand. **Fails closed** when the policy resolves to zero approvers.

**6 — The agent must never write `Accepted`.** `adr-author/SKILL.md` × 6 files,
byte-identical per `tests/test_adr_contract_consistency.py:107-118`: the agent
authors `Proposed` and stops. **This is the payload half of the whole decision** —
without it the record still says whatever the agent typed, and the gate is
cleanup after the fact.

**7 — Templates × 3.** Replace the empty `Approved by:` name fields with a
statement that `Accepted` is derived and where provenance comes from. Do **not**
touch ADR-0001's content: `tests/test_evidence.py` treats it as an authority the
code obeys, so its blast radius is wider than it looks.

**8 — Docs.** `ci/README.md` — delete the *"ADR required when preflight flags it
| No ADR validation"* row, which this work closes; add the gate to the Quick
Start table and a `permissions:` note to Required Secrets; document the
CODEOWNERS + required-reviews + branch-protection setup the model assumes. Plus
README commands table, CHANGELOG.

---

## Verification

```bash
./run_tests && ./full_test
pytest -k parity && pytest tests/test_adr_contract_consistency.py
```

Then against the real CLI:

```bash
govkit apply --type data --level 4 --target <sandbox>   # ships ADR-0001
govkit validate --target <sandbox>   # SILENT about ADR-0001 — govkit's decision, unmodified
# customer adds their own ADR saying Accepted
govkit validate --target <sandbox>   # WARN: claims Accepted, provenance verified in CI
# policy still holds the sentinel
govkit validate --target <sandbox>   # WARN: attestation not configured
```

The first case is the one that matters: a fresh `--type data` install must not
warn about the ADR govkit put there.

## Honest limits to state in the docs

- **The gate only sees ADRs changed in the PR.** An `Accepted` ADR merged before
  adoption keeps its status forever. That is the migration posture working as
  intended, not a hole to fix later.
- **Without branch protection the gate is advisory.** govkit can verify an
  approval happened; only the platform can make the check required. That is why
  this ships as "govkit verifies, platform enforces", and why the CODEOWNERS
  documentation is part of the deliverable rather than an optional extra.
- **Azure is the bigger lift.** No shipped Azure template calls a platform API or
  uses `System.AccessToken`; the GitHub half has `gh api` available in the runner.

---

## Repo state when this plan was written

- `main` at `89195a7`, 2626 fast + 134 e2e tests passing, working tree clean.
- Version `0.18.0`. **Eight CI templates pin `govkit~=0.18.0`**, and
  `tests/test_ci_govkit_dependency.py` asserts the pin equals `pyproject.toml`.
  A release bump must update both in the same commit — see `CONTRIBUTING.md`
  under *Modifying CI Pipelines*. This will be the first release since that rule
  existed.
- Job names already taken across `ci/github/` — `adr-approval-check` is free:
  `boundary-check`, `data-common-gate`, `databricks-gate`, `dbt-gate`, `deepeval`,
  `eval-gate`, `llm-eval`, `evidence-check`, `fix-lane-check`, `guardrails`,
  `commit-format`, `sonarqube`, `security-scan`, `quality`, `lint`, `unit-tests`,
  `build-smoke`, `topology-check`, `system-prompt-check`, `promptfoo`,
  `schema-validation`, `contract-compatibility`, `governance-artifacts`,
  `repo-scope-check`, `eval-prediction-check`, `e2e-playwright`,
  `accessibility-report`, `playwright`, `type-check`, `component-tests`,
  `bundle-size`.
- Manifests are hand-formatted with compact arrays. **Do not JSON round-trip
  them** — it reformats ~1449 lines and buries the real change. Use targeted
  insertion with a bracket-matching scanner.
- `.gitignore` carries an unstaged edit that predates this work and belongs to
  the user. Leave it out of every commit.
