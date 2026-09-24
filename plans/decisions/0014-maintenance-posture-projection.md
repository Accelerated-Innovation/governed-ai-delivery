# ADR 0014: Privacy-filtered maintenance posture projection

Status: accepted for I11a implementation, 2026-09-24.

## Context

I09 already owns maintenance decisions and I10 supplies canonical provider facts.
Those local records contain paths, source references and diagnostic prose that are
unsuitable for a default shareable report. I11 must preserve authoritative facts
without creating another assessment engine or equating installation with execution.
I10's protected-caller deployment acceptance remains open; this does not prevent
core reporting of the integrated facts and their unknown coverage.

## Decision

Add pure `posture.py` projection/replay and a dedicated `posture export` registrar.
Accept only a replayable saved maintenance assessment. Reuse its canonical states,
findings/actions and CheckReport aggregation. Do not inspect the repository, choose
new versions, infer approval, run commands or refresh metadata during export.

Use a strict versioned schema and explicit field allowlist. Replace free text,
paths, URLs and custom identifiers with category-scoped deterministic references.
Keep constrained categories, public capability labels, source timestamps, exception
expiry and public version displays. Retain exact versions by reference without
printing local labels. References are pseudonymous, not anonymized or authenticated.
Local JSON Pointers connect recommendations/resources/candidates to the private
source assessment without exporting its location or payload.

Render human output from the same projected object. Successful export exits zero
regardless of maintenance health; the canonical maintenance state/exit code remains
explicit. Publication is opt-in, outside the assessed target, create-only/private,
and delegates to the established artifact writer. No automatic transmission.

## Consequences and deferred scope

Readers can compare saved snapshots and inspect canonical next actions without raw
source exposure. Full local reason/evidence and prerequisite text stays in the
source assessment; no action is authorized by an exported reference. Snapshot
consistency is not authenticity or current freshness. Maintenance execution is not
project-control execution. No score, individual tracking or productivity claim.

I11a covers maintenance posture, strict projection/privacy, human/JSON parity and
explicit publication. I11b retains change workflow/evaluation evidence, aggregate
metrics with denominators, the full scenario set and a separate voluntary team
pilot protocol. #148 remains open; no acceptance is waived. #147 remains open for
protected-caller/path-coverage deployment evidence. Installer source is not yet
self-hosted; use isolated consumer fixtures.

Sequencing update: [ADR 0015](0015-change-posture-projection.md) delivers change
projection in I11b and groups aggregation, the complete maintenance scenario set
and the voluntary protocol into I11c. The separate snapshot contracts must be
reviewed before their aggregation rules; the original acceptance scope is retained.
