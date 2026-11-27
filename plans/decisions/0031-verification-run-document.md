# ADR 0031: A verification run is built offline, as a document

Status: Proposed with the PR for #279. Merging that PR accepts the contract below.

## Context

The Product Definition Graph records verification runs: what one build's tests and evaluations found, each result bound to the revision that ran (`POST /v1/verification-runs` in `discovery-engine`). The evidence report already holds the graph's identifiers, revision digests and outcomes (ADRs 0022 to 0024). Nothing projects it into a run.

The engine's contract constrains the design:

- The request model refuses unknown keys. A result holds an identifier, a revision digest, a kind and an outcome.
- The whole run is refused when one result names a requirement the baseline does not hold, or holds at another revision.
- A run is immutable. An identical re-send returns the stored run; a different run under the same reference is a conflict.
- Scores on a result are specified in discovery-engine#303 and not implemented.

The maintainer decided on 2026-11-27:

- Build against the contract the engine runs today. Scores wait for contract version 2.
- Two PRs: this one builds the document; the next posts it and adds the CI step.
- A result the baseline does not hold at that revision is left out and listed.
- The CI step will run on the default branch only, and ships off.

## Decision

1. **A new command, `govkit verification-run build`.** It reads the target and writes one `govkit.verification-run` document to standard output or to a new file outside the target. It opens no connection.
2. **The request is an allowlist.** `request` holds exactly the keys the engine accepts. Titles, paths, messages and scores are never in it. What was left out is beside it, and is not sent.
3. **Every feature, one run.** The run covers every feature under `features/`, apart from starter features. A caller cannot narrow it.
4. **Results count only when recorded and clean.** A feature's results are sent only when its evidence record is current and the recorded tree matched its commit. A run names a commit, and a tree with uncommitted changes ran other code.
5. **The commit and time come from the record.** `build.commit` is the recorded commit and `executed_at` is when the record was written. Two builds of the same results are identical, so a re-send is not a conflict.
6. **The baseline is read from the tag in the checkout.** GovKit computes each requirement's identifier and digest from the tagged files, with the same code as the report. Only `refs/tags/` is read. A result the tag does not hold at that revision is left out with a reason.
7. **A hidden skip is not sent as a pass.** When a result file counts skipped tests it does not mark, passed test results are left out.
8. **The caller states the rest.** The repository, the baseline tag, the run reference, the build reference and the artifact link are options, each held to the engine's rule.
9. **Exit status.** 0 when a request was built, 1 when nothing can be sent, 2 when the run could not start.

## Alternatives considered

- **Send everything and let the engine refuse.** Any feature work since the baseline would make every push fail until a new baseline is indexed.
- **Stop when a result would be refused.** The same blocking effect, with a clearer message.
- **One command that builds and posts.** The first network write in GovKit would arrive with the projection, and the payload could not be reviewed before it is sent.
- **Use the current time for `executed_at`.** A rebuilt run would differ from the stored one and be refused as a conflict.
- **Send results from an uncommitted tree.** The graph would hold results for code no commit names.
- **Build measurements now from the proposed engine ADR.** The shape is not accepted and no engine accepts it.

## Consequences

- **The comparison is local.** GovKit reads its own checkout's tag. The engine may have indexed something else, and may still refuse the run.
- **The engine's rules are copied by hand.** The patterns and limits in `verification_run.py` come from the engine's source. A published request schema (E4) would replace the copy.
- **A scenario edited since the baseline is silent in the graph until the next baseline.** The document lists it; the graph shows it as stale or unverified.
- **An edit to `eval_criteria.yaml` leaves out every criterion in it,** because a criterion's revision is the file's digest.
- **A repository with SHA-256 object names cannot build a run.** The engine accepts 40-character commits only.
- The reasons, the document kind, the option names and the exit codes are a public contract: add, never rename.
