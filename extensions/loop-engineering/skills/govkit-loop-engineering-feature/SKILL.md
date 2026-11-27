---
name: govkit-loop-engineering-feature
description: Work on one feature in rounds until GovKit answers done, and stop for a person on escalate, on no progress or at the round limit.
---

# Feature loop

Work on one feature in rounds. After each round, GovKit answers `done`, `continue` or `escalate` for that feature. You stop when the rules below say so. GovKit does not run this loop; you do.

Read [the round and the stop rules](references/feature-loop.md) before you start. In Claude Code, also read [driving the loop in Claude Code](references/claude-code.md).

## Before the first round

Get these from the person who starts the loop. Do not guess any of them.

- The feature's name: a directory under `features/`.
- The request file, the base commit and the accepted policy checkout that `govkit conform` needs.
- The command that runs the tests and writes JUnit XML.
- The round limit. It is 10 unless the person states another number.

## One round

1. Make the change the reasons call for. In the first round, implement the feature.
2. Run the tests.
3. Run `govkit evidence --target . --record`.
4. Run `govkit conform` with the request, the base, the policy checkout and `--feature <name>`.
5. Act on the exit status.

| Exit | State | What you do |
|---|---|---|
| 0 | `done` | Stop and report |
| 1 | `continue` | Read every reason, then start the next round, unless a stop rule applies |
| 3 | `escalate` | Stop and hand over to a person |
| 2 | The run could not start | Stop and report the message. Do not retry with changed inputs |

## Stop rules

Stop and hand over to a person when any of these is true:

- The state is `escalate`.
- Two rounds in a row give the same set of reason codes. You are not making progress.
- You have completed the round limit.

## What you must not do

- Do not edit `acceptance.feature`, `eval_criteria.yaml` or an existing test to reach done. GovKit reports that as `definition-changed` or `protected-changed`, and the state becomes `escalate`.
- Do not skip a test, or mark one as expected to fail, to reach done.
- Do not start a paid evaluation or one that needs a person. GovKit reports those as owed.
- Do not write the results by hand. Results come from the test run.
- Do not call a local `done` approved, reviewed or ready to merge.

## What you report when you stop

- The final state, and how many rounds you ran.
- Every reason code and message from the last run, as GovKit printed them.
- Which stop rule applied.
- What you changed.

A loaded skill is guidance, never evidence that a check passed. Accepted project policy remains authoritative.
