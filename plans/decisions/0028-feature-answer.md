# ADR 0028: One answer per feature: done, continue or escalate

Status: Proposed with the PR for #271. Merging that PR accepts the contract below.

## Context

`govkit evidence --feature` reports whether a feature's scenarios and criteria have current passing results. `govkit conform --request` reports whether the change meets its required checks and whether it weakened the definition or the files that check it (ADRs 0026 and 0027). An agent or a pipeline needs one answer from both.

A two-state answer is not enough. When the only thing left is a paid evaluation or a skipped test, "not done" keeps an agent working on something it cannot legitimately fix.

The maintainer decided on 2026-11-26:

- The answer comes from `govkit conform --feature`, in the existing change run.
- A stale, unrecorded or missing free result is work for the agent, not for a person.
- There is no service reachability check.

## Decision

1. **`--feature NAME` on the change run.** It needs `--request`, `--base` and `--policy-target`, as every change run does. Without `--feature`, output and exit status are unchanged.
2. **The evidence joins the change report.** The feature's evidence report is a required check, `evidence:feature`. It is read before any check runs, so a command that `conform` itself executes cannot supply the results it is judged by.
3. **Three states, chosen in order.**
   1. `escalate` when `change:definition` or `change:protected` failed, a test or evaluation ended in an error, or the evidence could not be read.
   2. `continue` when a scenario or criterion failed, a free result is missing, the results are stale, unrecorded or tied to an unusable record, or any other check failed.
   3. `escalate` when anything else required is not a pass: an owed paid or human evaluation, a skipped test, unmarked skips, criteria in a form that is not compared, a feature with no scenarios, or a required check with no passing result.
   4. `done` when there is no reason at all.
4. **Every reason is listed.** Each has a stable code, the check it came from, the requirements it concerns, and says who can act on it.
5. **Exit status.** 0 for done, 1 for continue, 3 for escalate. With `--feature`, a run that could not start exits 2, because 1 means continue.
6. **The answer document.** `--json` prints `govkit.feature-verdict`. It holds the evidence report and the change results unchanged, each valid against its own schema. `parse_feature_verdict` recomputes the answer from them and checks that the evidence is the report the change results checked.
7. **`feature_verdict.py` is pure.** It reads the evidence report and the check states, and nothing else.

## Alternatives considered

- **`govkit evidence --feature --base`.** Lighter locally, but the protected-file check needs the policy checkout, so a local done could be reached without it.
- **Adding the answer to `change-results`.** Posture and pipeline evidence read that record with strict schemas. A separate document leaves them unchanged.
- **Counting a result only when `conform` ran the tests itself.** A paid or human evaluation can never be run that way, so no feature with one could be done.
- **Escalating on every inconclusive item**, as the plan first said. A loop would stop for a person each time the agent had not rerun or recorded its tests.

## Consequences

- **A local done is a stop condition, not a gate.** A result file and its record are observations. They do not prove that the tests ran. The run that counts is CI on a clean checkout.
- **`evidence:feature` passes on result files.** Its evidence is a local check of files in the checkout, with that limit stated. A record can be rewritten without running the tests again.
- **A required check that cannot pass locally ends in escalate.** Platform approval is one. The agent does what it can, and the answer then names what a person or CI must supply.
- **An errored test escalates** even where an agent could fix it, because an error is not a failed assertion.
- **A command that `conform` executes may rewrite result files.** They are then newer than the record, and the next run reports the results as stale until they are recorded again.
- **The feature artifact checks of `govkit validate` are not part of the answer yet.** That is L07b.
- Reason codes, states and exit codes are a public contract: add, never rename.
