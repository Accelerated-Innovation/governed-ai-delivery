# Cross-Repository Governance Plan

> **Purpose:** Extend governance system to detect, prevent, and guide agents away from writing code that belongs in other repositories. Ensures Gherkin specs and NFRs that describe cross-cutting solutions don't result in agents implementing code in the wrong repo.
>
> **Status:** Draft
> **Last Updated:** 2026-04-22

---

## Problem Statement

Currently, the governance system enforces **within-repo boundaries** (Hexagonal Architecture layers) but has **zero awareness of repository boundaries**. If a Gherkin feature and NFRs describe work spanning multiple repos (e.g., "Auth Service publishes JWKS, Client validates token locally"), agents can write implementation code in any repo without safeguards.

**Risk:** Agent writes Client-side JWT validation in the Auth Service repo, or adds dependencies that don't belong.

**Solution:** Extend architecture-preflight, rules, and CI to make repo ownership explicit in specs and validate during planning and implementation.

---

## Four-Tier Implementation Plan

### Tier 1: Spec Clarity — Template Updates

Make "Repository Scope" mandatory in all feature specs before agents plan implementation.

| Item | Task | Artifact | Owner |
|------|------|----------|-------|
| **1.1** | Add "Repository Scope" section to backend NFR template | `governance/backend/templates/nfrs.md` | Platform |
| **1.2** | Add "Repository Scope" section to UI NFR template | `governance/ui/templates/nfrs.md` | Platform |
| **1.3** | Add "Repository Scope" section to CLI NFR template | `governance/backend/templates/nfrs.md` (if separate) or backend | Platform |
| **1.4** | Update starter features: `starter_backend/nfrs.md` | Populate with example repo scope | Platform |
| **1.5** | Update starter features: `starter_ui/nfrs.md` | Populate with example repo scope | Platform |
| **1.6** | Update starter features: `starter_cli/nfrs.md` | Populate with example repo scope | Platform |
| **1.7** | Update L3 starter features with repo scope | All `*_l3/nfrs.md` files (6 files) | Platform |

**Acceptance:** Every new feature created via `govkit init` includes "Repository Scope" section with checklist and owner mapping.

---

### Tier 2: Agent Rules — Repo Scope Enforcement

Create new rule file for all three agents that gates implementation on repo scope clarity and prevents out-of-scope code writes.

| Item | Task | Artifact | Owner |
|------|------|----------|-------|
| **2.1** | Create Claude Code repo scope rule | `agents/claude-code/rules/generic/repo-scope.md` | Platform |
| **2.2** | Create Copilot repo scope instruction | `agents/copilot/instructions/generic/repo-scope.instructions.md` | Platform |
| **2.3** | Create Codex repo scope rule | `agents/codex/rules/generic/repo-scope.md` | Platform |
| **2.4** | Update Claude Code spec-compliance rule to reference repo-scope | Add cross-ref to `agents/claude-code/rules/generic/spec-compliance.md` | Platform |
| **2.5** | Update Copilot spec-compliance instruction to reference repo-scope | Add cross-ref to copilot instructions | Platform |
| **2.6** | Update Codex spec-compliance rule to reference repo-scope | Add cross-ref to `agents/codex/rules/generic/spec-compliance.md` | Platform |

**Acceptance:** All three agents reject planning requests when repo scope is undefined; rule clearly forbids code writes outside ownership scope.

---

### Tier 3: Architecture Preflight Skills — Repo Scope Analysis

Update preflight skills/prompts for all three agents to validate repo scope and flag cross-repo dependencies.

| Item | Task | Artifact | Owner |
|------|------|----------|-------|
| **3.1** | Add "Repository Scope Analysis" section to Claude Code backend preflight | `agents/claude-code/skills/backend/architecture-preflight/SKILL.md` | Platform |
| **3.2** | Add "Repository Scope Analysis" section to Claude Code UI preflight | `agents/claude-code/skills/ui/architecture-preflight/SKILL.md` | Platform |
| **3.3** | Add "Repository Scope Analysis" section to Copilot backend preflight prompt | `agents/copilot/prompts/backend/architecture-preflight.prompt.md` | Platform |
| **3.4** | Add "Repository Scope Analysis" section to Copilot UI preflight prompt | `agents/copilot/prompts/ui/architecture-preflight.prompt.md` | Platform |
| **3.5** | Add "Repository Scope Analysis" section to Codex backend preflight | `agents/codex/skills/backend/architecture-preflight/SKILL.md` | Platform |
| **3.6** | Add "Repository Scope Analysis" section to Codex UI preflight | `agents/codex/skills/ui/architecture-preflight/SKILL.md` | Platform |
| **3.7** | Create shared content snippet for "Repository Scope Analysis" | `docs/REPO_SCOPE_ANALYSIS_GUIDANCE.md` | Platform |

**Content for all preflight updates:**
```
## N. Repository Scope Analysis

Before planning cross-repo work:

1. Check `nfrs.md` — does "Repository Scope" section exist and is it complete?
   - [ ] Single repo only — proceed normally
   - [ ] Multiple repos — all repos listed with owner names

2. For each repo listed as owner:
   - Confirm THIS repo is the primary owner or a listed owner
   - If NOT listed, HALT — this feature is out of scope
   - Document which modules/services in THIS repo will be affected

3. For each external repo dependency:
   - Document the contract it will use (e.g., "Auth Service JWKS endpoint", "API Gateway JWT relay header")
   - Confirm the contract is defined in a shared schema or external docs
   - Note: implementation of the contract belongs in the external repo

4. If repo scope is incomplete or ambiguous:
   - HALT and request clarification from the feature owner
   - List what's missing: owner mapping, contracts, or dependency details
```

**Acceptance:** All three agents ask repo scope questions during preflight; unclear scope blocks plan generation.

---

### Tier 4: CI Validation — Repository Boundary Checks

Add repo-specific validation to CI templates so each repo can enforce its ownership boundaries.

| Item | Task | Artifact | Owner |
|------|------|----------|-------|
| **4.1** | Create repo-scope-check job template (GitHub Actions) | `governance/ci/github/repo-scope-check.yml` | Platform |
| **4.2** | Create repo-scope-check job template (Azure Pipelines) | `governance/ci/azure/repo-scope-check.yml` | Platform |
| **4.3** | Document repo-scope-check in CI README | Update `ci/README.md` — explain how each repo configures ownership | Platform |
| **4.4** | Add instructions to each starter template | GitHub/Azure workflow README in starter features | Platform |

**Job Behavior:**
```
For each modified feature's nfrs.md:
  1. Extract "Repository Scope" section
  2. Get THIS_REPO from .govkit marker (or GIT_REMOTE)
  3. Fail if THIS_REPO is not listed as owner OR owner list is empty
  4. Warn if feature touches non-owned modules (optional, advisory)
  
Result: PASS only if repo ownership is explicit and matches THIS_REPO
```

**Acceptance:** Repo-scope validation is available in both GitHub and Azure templates; each repo can opt in to enforce.

---

### Tier 5: Documentation & Guidance

Create user-facing documentation so teams understand how to scope cross-repo features.

| Item | Task | Artifact | Owner |
|------|------|----------|-------|
| **5.1** | Create cross-repo feature guide | `docs/CROSS_REPO_FEATURES.md` | Platform |
| **5.2** | Add "Multi-Repo Features" section to README | Link to guide, brief overview | Platform |
| **5.3** | Add example: multi-repo auth feature | Gherkin + NFRs for realistic scenario | Platform |
| **5.4** | Update BOUNDARIES.md to reference repo-scope | Note that layer boundaries are within-repo; repo boundaries are separate | Platform |
| **5.5** | Add FAQ entry: "My feature spans 3 repos, how do I structure it?" | `README.md` → Troubleshooting section | Platform |

**Content for `docs/CROSS_REPO_FEATURES.md`:**
- When to split features across repos vs. monorepo features
- How to define clear contracts between repos (JWKS endpoint, message schemas, API contracts)
- Repo ownership mapping table (who owns what)
- Example: Auth Service + API Gateway + Client SDK feature split
- How to write tests that span repos (contract tests, integration tests)

**Acceptance:** Teams can self-serve guidance on structuring cross-repo work.

---

## Dependency Graph

```
Tier 1 (Spec Clarity)
  ↓
Tier 2 (Agent Rules) — blocks planning if spec is incomplete
  ↓
Tier 3 (Preflight Skills) — validates repo scope during architecture analysis
  ↓
Tier 4 (CI Validation) — enforces at merge time
  ↓
Tier 5 (Documentation) — enables team self-service
```

**Critical Path:** 1.1 → 1.2 → 2.1 → 2.2 → 2.3 → 3.1 → 3.2 → 3.3

(Other items can proceed in parallel once dependencies are met)

---

## Working Agreement

- Each item = one atomic commit
- Related items within a tier may be combined if they touch the same file
- Commit format: `feat(governance): <description>` or `docs(governance): <description>`
- Tiers should be completed in order (1 → 2 → 3 → 4 → 5)
- Items within a tier can proceed in parallel
- This file is the source of truth; mark items complete as work progresses

---

## Checklist

### Tier 1: Spec Clarity
- [ ] 1.1 Backend NFR template
- [ ] 1.2 UI NFR template
- [ ] 1.3 CLI NFR template (if separate)
- [ ] 1.4 starter_backend example
- [ ] 1.5 starter_ui example
- [ ] 1.6 starter_cli example
- [ ] 1.7 L3 starters (6 files)

### Tier 2: Agent Rules
- [x] 2.1 Claude Code repo-scope.md
- [x] 2.2 Copilot repo-scope.instructions.md
- [x] 2.3 Codex repo-scope.md
- [x] 2.4 Claude Code spec-compliance cross-ref
- [x] 2.5 Copilot spec-compliance cross-ref
- [x] 2.6 Codex spec-compliance cross-ref

### Tier 3: Preflight Skills
- [x] 3.1 Claude Code backend preflight
- [x] 3.2 Claude Code UI preflight
- [x] 3.3 Copilot backend preflight
- [x] 3.4 Copilot UI preflight
- [x] 3.5 Codex backend preflight
- [x] 3.6 Codex UI preflight
- [x] 3.7 Shared guidance doc

### Tier 4: CI Validation
- [ ] 4.1 GitHub Actions job template
- [ ] 4.2 Azure Pipelines job template
- [ ] 4.3 CI README documentation
- [ ] 4.4 Starter template instructions

### Tier 5: Documentation
- [ ] 5.1 Cross-repo features guide
- [ ] 5.2 README multi-repo section
- [ ] 5.3 Example multi-repo feature
- [ ] 5.4 BOUNDARIES.md update
- [ ] 5.5 FAQ entry

---

## Notes

- **Backward Compatibility:** Existing features without "Repository Scope" section will fail preflight validation (intentional — forces spec clarity)
- **Multi-Repo Testing:** Integration tests that span repos should be documented in Tier 5 guide
- **Monorepo Considerations:** Single-repo projects can check "This repo only" and skip repo scope validation
- **Future:** Could extend to validate inter-repo contract definitions (JWKS schemas, message protocols, etc.)
