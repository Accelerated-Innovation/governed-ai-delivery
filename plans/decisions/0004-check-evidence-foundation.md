# ADR 0004: Shared check results and explicit evidence boundaries

Status: implementation decision for I04, subject to maintainer review.
Date: 2026-09-23.
Issue: [#146](https://github.com/Accelerated-Innovation/governed-ai-delivery/issues/146).
Predecessor: [ADR 0003](0003-capability-pack-installation.md).

## Decision

Add `govkit conform` as a thin registrar over a shared repository assembly service. Typed check specifications, outcomes, findings and evidence live in `check_models.py`; the explicit registry and runner live in `check_runner.py`. `check_adapters.py` adapts real existing domain checks and pinned controls. Registration does not dynamically import code named in a result file.

Keep applicability/mandatory policy separate from execution and outcome. Preserve every required selection and its accepted policy source; missing providers remain unknown. The runner isolates exceptions, process exits, output violations and malformed returned data per check. Checks return facts rather than printing. Aggregate counts and exit status are derived from the same results used by human and JSON renderers. No non-pass state satisfies a required control, including an asserted waiver.

Use a strict versioned runtime schema for raw reports and validate each outcome before aggregation. Replay verifies canonical identities and counts for inspection, never trust/authentication. Identity includes explicit nullable revision/change/time facts and profile/resolution/lock digests. Evidence describes source, scope, method, claimed origin and limitations; agent predictions remain producer assertions. Content hashes and claimed origin labels cannot authenticate their authors.

Legacy public commands retain behavior. Extract a doctor inspection seam with an explicit marker; inject marker/schema boundaries into feature checks and schema/ADR inventory boundaries into approval checks. Default conformance reads cannot trigger legacy marker migration. Local schema validation uses the existing runtime JSON Schema dependency and refuses external references, so it needs neither network nor optional validation binaries. Unreadable inventories cannot become verified empty inventories. Legacy doctor heuristics may omit indeterminate observations; clean output therefore remains unknown in the new report.

Pack execution requires an explicit ID opt-in, verifies pinned code and produces a narrow exit-result observation. Default inspection never executes arbitrary pack code. Native skill drift is assessed separately and does not itself prevent a pinned control from running. Pack execution is not sandboxed.

## Limits

This foundation does not implement actual-diff routing, conditional workflow applicability, scoped architecture transitions, authorized waivers, external report ingestion as evidence, live provider attestations or maintenance assessment. Those remain I06–I11. Output guards are sequential and process-global; concurrent callers need separate processes. Runtime checks do not promise isolation from hostile in-process code. Reporting snapshots do not guarantee consistency against concurrent filesystem edits. The source repository is not self-hosted by this change.
