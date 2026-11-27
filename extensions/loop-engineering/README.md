# Loop Engineering

Guidance for an agent that works on one feature in rounds until GovKit answers that it is done.

GovKit does not run the loop. It does not start, schedule or re-prompt an agent. The agent's own tools own the iteration. This pack supplies the instructions for a round, the rules for stopping, and what to report.

## What it holds

- `govkit-loop-engineering-feature`: the feature loop. A round is a change, a test run, `govkit evidence --record` and `govkit conform --feature`. The agent stops on done, on escalate, when two rounds give the same reasons, or after a stated number of rounds.
- Inside that skill, `references/claude-code.md`: how to drive the loop in Claude Code. The skill itself is the same for every agent.

## What it needs

- A GovKit release that has `govkit conform --feature`.
- A test command that writes JUnit XML.
- A request file, a base commit and an accepted policy checkout, as `govkit conform` requires. See `docs/CHANGE_CONFORMANCE.md` in GovKit.

## What it is not

- It adds no check and no command. Removing it changes no required control.
- A loop that ends in done is a stop condition for the agent. It is not review, approval or a gate.
- Installing the pack does not accept its guidance as project policy. Select it explicitly in the desired profile.
