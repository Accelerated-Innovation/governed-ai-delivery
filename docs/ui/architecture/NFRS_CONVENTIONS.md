# NFRs Conventions — UI

This document defines the section contract for every `nfrs.md` file in a UI project.

These conventions are binding. All agents must reference this document when reviewing or generating a UI `nfrs.md`.

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
| `## Repository Scope` | Always present. Declares `single-repo` or `multi-repo` (with the cross-repo table completed for multi-repo). | `repo-scope-check` CI + Architecture Preflight §2.5 (HALT if incomplete) |
| At least one NFR category | At least one category section below must be populated (non-`TBD`). | Architecture Preflight + Gherkin coverage |

Standard UI NFR category sections:

`## Accessibility`, `## Performance`, `## Browser Compatibility`, `## Usability`,
`## Dependencies`, `## Testing Requirements`.

Accessibility is first-class for UI: the `## Accessibility` category should target
WCAG 2.1 Level AA with zero critical/serious axe-core violations (see
[ACCESSIBILITY_STANDARDS.md](ACCESSIBILITY_STANDARDS.md)). Accessibility scenarios in
`acceptance.feature` use the `@accessibility` tag.

---

## 3. Recommended Sections

| Section | Rule | Behaviour when absent |
|---|---|---|
| `## Out of scope` | Lists capabilities deliberately deferred to a later increment or a separate feature. | Spec planning **infers** the deferrals and labels the plan's `### Out of scope` with `<!-- INFERRED -->`, then asks the feature owner to confirm. |

`## Out of scope` is the canonical home for "we are not building X yet" intent. When
present, spec planning copies its entries into `plan.md` `### Out of scope` **verbatim**
(author-declared). When absent, the deferrals are inferred and marked — see the Scope
Boundary Source Check (§2.7) in the UI Architecture Preflight.

Do **not** encode deferrals as negative Gherkin steps (`And no X is introduced`): those
are unfalsifiable assertions. Deferrals belong in this section.

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
| `ci/<provider>/repo-scope-check.yml` | Repository Scope completeness | FAIL (CI) |
| UI Architecture Preflight §2.5 / §2.7 | Repository scope, Out-of-scope source | HALT / note |

---

## 6. Minimal Compliant Example

```markdown
# Non-Functional Requirements: <feature_name>

## Repository Scope

**Scope:** `single-repo`

## Out of scope

- <deferred capability> — later increment

## Accessibility
- WCAG 2.1 AA; zero critical/serious axe-core violations

## Performance
- <requirement>
```

---

See also: [MVVM_CONTRACT.md](MVVM_CONTRACT.md) |
[ACCESSIBILITY_STANDARDS.md](ACCESSIBILITY_STANDARDS.md) |
[REPO_SCOPE_ANALYSIS_GUIDANCE.md](../../REPO_SCOPE_ANALYSIS_GUIDANCE.md)
