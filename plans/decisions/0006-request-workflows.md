# ADR 0006: Local normalized intent and additive workflow plans

Status: accepted for I06 implementation (#179).

## Context

Repository installation is stable across different requests. Legacy maturity levels must not force a five-document feature workflow on a bounded enhancement, or allow a defect label to bypass sensitive controls. Existing I02/I03 profiles and locks establish accepted requirements and pinned resources; I04 separates obligations from executed evidence.

## Decision

Add `govkit request template/plan`. Human/agent normalization precedes the deterministic boundary. The template deliberately starts proposed with unknown impacts; a caller-reviewed local record preserves summary, acceptance, source and scope without a live ticket dependency. A pure resolver takes validated profile, request and captured resource/evidence context. The read-only adapter verifies pins and observes bounded local reference content. The CLI only renders results.

Workflow selection is additive: repository controls, required pinned checks, impact controls and matching accepted workflow policy all remain. Policy requiring Gherkin escalates bounded/defect planning to full delivery and evaluates newly applicable rules. LLM evaluation is independent. Unknown material inputs block readiness; missing capabilities produce explicit setup steps. Guidance paths come only from the verified current lock. Application Governance 1.1.0 ships the shared normalization/planning skill to all three native agent layouts.

Versioned schemas cover normalized requests, scope observations, captured context and replayable plans. The plan exposes I04 `CheckSpec` and `Evidence` values without execution. Local source hashes and replay detect drift/inconsistency; they do not authenticate an author's assertions or decisions. Readiness means the planning inputs are resolved, not that tests passed or architecture was approved.

## Consequences and boundary

Bounded work keeps a compact change record plus test evidence and reused accepted references. Defects retain the existing eligibility and red/green obligations. Sensitive/full-feature/architecture work retains applicable artifacts and checks. No automatic installation, policy waiver, tracker mutation, repository write or network call occurs.

Supplying expanded observed scope re-resolves the plan and identifies changed inputs. I07 owns trusted actual-Git-diff derivation and conformance enforcement; I06 cannot assert an editable normalized record is exhaustive. Current/target transition enforcement remains I07. Existing legacy commands and installation remain unchanged. The plan format is a versioned local record; it is not a signed attestation or stable release verdict.

Validation is test first: routing/side-effect/replay regressions, seven bundled examples, native guidance across three agents, the fast suite and a clean runtime-only wheel smoke. Qodo local review precedes PR creation per the standing delivery instruction.
