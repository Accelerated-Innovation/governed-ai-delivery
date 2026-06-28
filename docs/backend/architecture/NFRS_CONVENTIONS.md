# NFRs Conventions

This document defines the section contract for every `nfrs.md` file in this repository.

These conventions are binding. All agents must reference this document when reviewing or generating an `nfrs.md`.

`nfrs.md` is markdown (not structured data), so the contract is expressed as a set of
required and recommended `##` sections rather than a JSON Schema. It is enforced by
`govkit validate` (`check_nfrs_sections`, advisory), with the hard gates supplied by
`ci/<provider>/repo-scope-check.yml` and the Architecture Preflight.

---

## 1. File Naming and Location

Each feature's non-functional requirements live at:

```
features/<feature_name>/nfrs.md
```

One `nfrs.md` per feature folder.

---

## 2. Required Sections

| Section | Rule | Hard gate |
|---|---|---|
| `## Repository Scope` | Always present. Declares `single-repo` or `multi-repo` (with the cross-repo table completed for multi-repo). | `repo-scope-check` CI + Architecture Preflight §3.5 (HALT if incomplete) |
| At least one NFR category | At least one category section below must be populated (non-`TBD`). | Architecture Preflight §1 + Gherkin NFR coverage |

Standard backend NFR category sections:

`## Performance`, `## Availability`, `## Security`, `## Compliance`,
`## Scalability`, `## Observability`, `## Reliability`, `## Compatibility`,
`## Dependencies`, `## Testing Requirements`.

Every **populated** NFR category must have at least one matching `@nfr-*` scenario in
`acceptance.feature` — see [GHERKIN_CONVENTIONS.md](GHERKIN_CONVENTIONS.md) §2.

For `mode: llm` features, the LLM categories `## LLM Latency`, `## LLM Cost`,
`## LLM Fallback`, and `## LLM Safety` must additionally be populated (enforced by
`govkit validate` at Level 5).

---

## 3. Recommended Sections

| Section | Rule | Behaviour when absent |
|---|---|---|
| `## Out of scope` | Lists capabilities deliberately deferred to a later increment or a separate feature. | Spec planning **infers** the deferrals and labels the plan's `### Out of scope` with `<!-- INFERRED -->`, then asks the feature owner to confirm. |

`## Out of scope` is the canonical home for "we are not building X yet" intent. When
present and non-empty, spec planning copies its entries into `plan.md` `### Out of scope`
**verbatim** (author-declared). When absent or empty, the deferrals are inferred and marked — see the Scope
Boundary Source Check in the Architecture Preflight.

Do **not** encode deferrals as negative Gherkin steps (`And no X is introduced`): those
are unfalsifiable assertions that fail the FIRST *self-verifying* rubric. Deferrals belong
in this section.

---

## 4. TBD vs N/A

- No `TBD` token may remain in a finalized `nfrs.md` — `govkit validate`
  (`check_nfrs_no_tbd`) and the Architecture Preflight both stop on `TBD`.
- A non-applicable NFR category must be explicitly marked `N/A`, not left blank or `TBD`.

---

## 5. Validation

| Surface | What it checks | Severity |
|---|---|---|
| `govkit validate` → `check_nfrs_sections` | Required/recommended sections present | Advisory (WARN) — required sections are hard-gated elsewhere |
| `govkit validate` → `check_nfrs_no_tbd` | No `TBD` entries | FAIL |
| `govkit validate` → `check_gherkin_nfr_coverage` | Populated categories have `@nfr-*` tags | FAIL |
| `ci/<provider>/repo-scope-check.yml` | Repository Scope completeness | FAIL (CI) |
| Architecture Preflight §1 / §3.5 / §3.6 | Artifact review, repository scope, Out-of-scope source | HALT / note |

---

## 6. Minimal Compliant Example

```markdown
# Non-Functional Requirements: <feature_name>

## Repository Scope

**Scope:** `single-repo`

## Out of scope

- <deferred capability> — later increment

## Performance
- <requirement>

## Security
- <requirement>
```

---

See also: [GHERKIN_CONVENTIONS.md](GHERKIN_CONVENTIONS.md) |
[REPO_SCOPE_ANALYSIS_GUIDANCE.md](../../REPO_SCOPE_ANALYSIS_GUIDANCE.md) |
[evaluation/eval_criteria.md](../evaluation/eval_criteria.md)
