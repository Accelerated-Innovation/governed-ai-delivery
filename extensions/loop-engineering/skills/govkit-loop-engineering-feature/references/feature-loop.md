# The round and the stop rules

## The commands of a round

```bash
<your test command>                       # must write JUnit XML
govkit evidence --target . --record
govkit conform --request <request file> --base <base> \
  --policy-target <policy checkout> --feature <name>
```

Add `--execute-check <id>` only for a check the person told you to execute. Add `--json` to read the answer as a `govkit.feature-verdict` document.

Run the three commands in this order, every round. The record ties the result files to the commit and the working tree. Any change after it makes the results stale, and stale results do not count. That includes a file you add for your own notes.

## Reading the answer

GovKit lists every reason. Each has a code. The state is decided in this order:

1. `escalate` when a reason is present that needs a person now.
2. `continue` when a reason is present that you can act on.
3. `escalate` when a reason is present that needs a person once you have nothing left to do.
4. `done` when there is no reason.

### Reasons you can act on

| Code | What to do |
|---|---|
| `result-failed` | Fix the implementation, then run the tests again |
| `result-missing` | Write or bind the missing test, or run the free evaluation, then record |
| `results-stale` | Run the tests again and record |
| `results-unrecorded` | Run `govkit evidence --target . --record` |
| `record-unusable` | Run the tests again and record |
| `check-failed` | Resolve the findings of the check that failed |

### Reasons that need a person now

`definition-changed`, `protected-changed`, `result-error`, `evidence-unreadable`, `check-error`.

Stop at once. Do not try to undo the cause and run again without saying so: report what happened.

### Reasons that need a person once you have nothing left to do

`result-skipped`, `result-owed`, `skips-unmarked`, `criteria-not-compared`, `no-scenarios`, `check-not-satisfied`, `evidence-inconclusive`.

While a reason you can act on is also present, the state is `continue`. Work on that one. When only these remain, the state is `escalate`.

## The stop rules

| Rule | When it applies |
|---|---|
| Done | Exit status 0 |
| Escalate | Exit status 3 |
| Could not start | Exit status 2 |
| No progress | The set of reason codes is the same as in the round before |
| Round limit | You have completed the stated number of rounds. The default is 10 |

Compare the codes, not the messages. Two rounds with `result-failed` are the same set even when another scenario failed.

Count a round each time you run `govkit conform --feature`. A round that only ran the tests and recorded, to clear `results-stale`, still counts.

## What a done means

A local `done` shows that result files exist for the commit and the working tree, and that every required check passed on this machine. It is not proof that the tests ran, and it is not review or approval. CI runs the same command with its own results.
