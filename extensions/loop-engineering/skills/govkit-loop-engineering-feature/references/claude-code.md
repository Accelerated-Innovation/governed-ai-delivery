# Driving the loop in Claude Code

This file applies to Claude Code only. The skill and its stop rules are the same for every agent.

The commands below were checked against the Claude Code documentation on 2026-11-27. Claude Code changes; check its documentation when something here does not match what you see.

## Use `/goal` for the loop

`/goal <condition>` keeps the session working until the condition is met. After each turn a separate model reads the conversation and decides whether the condition holds.

That model runs no command. It only reads what is in the conversation. So in every round, print the exit status of `govkit conform --feature` and the state it gave. A condition that cannot be seen in the output is never met.

Put all the stop rules in the condition, not only done. A condition that names only done keeps the session working after an escalate.

```
/goal Follow the govkit-loop-engineering-feature skill for feature 07_invoice_approval.
Stop when the last `govkit conform --feature` run printed in this conversation exited 0 (done),
or exited 3 (escalate), or exited 2 (could not start),
or two rounds in a row gave the same reason codes,
or 10 rounds have run. Then report as the skill says.
```

- `/goal` has no turn limit or time limit of its own. The round limit in the condition is the limit.
- `/goal` alone shows the goal. `/goal clear` removes it.
- A session has one goal. A new one replaces it.

## Running without a person at the keyboard

`claude -p "/goal <condition>"` runs the same loop to completion. Add limits that do not depend on the condition:

- `--max-turns <n>` limits the turns.
- `--max-budget-usd <amount>` stops the run once the estimated spend reaches the amount. It is an estimate, and the spend can pass it.

A run with no person cannot answer a permission prompt. Before you start one, the person must allow what a round needs: editing files, the test command and the two `govkit` commands. Allow those and no more, through Claude Code's permission settings, as its documentation describes. A limit on turns or spend is a separate control and does not replace this.

## What not to use for this loop

- **`/loop`** repeats a prompt on an interval while the session is open. It suits a check that waits on something outside the session, such as a CI run. A feature loop has nothing to wait for between rounds.
- **`/schedule`** runs in the cloud from a fresh clone. It has no access to your working tree, so the results and the record of your local run are not there.
- **A Stop hook that blocks until `govkit conform` exits 0.** It would send you back to work after an escalate and after a round with no progress, which are the cases where you must stop. If a project uses a Stop hook here, it must block only on exit status 1 and must let every other status through.

## What stays true

GovKit does not start, schedule or re-prompt you. A goal that is met is the stop condition of this session. It is not review, approval or a gate.
