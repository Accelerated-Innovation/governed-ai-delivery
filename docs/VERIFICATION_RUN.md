# Verification run

`govkit verification-run build` turns a build's recorded results into a verification run for the Product Definition Graph. It writes one document and sends nothing.

A verification run tells the graph what one build's tests and evaluations found. Each result names a scenario or a criterion and the exact revision that ran.

```bash
pytest --junitxml=junit.xml
govkit evidence --target . --record
govkit verification-run build --target . \
  --baseline v1.4.0 \
  --repository acme/invoices \
  --run-reference github:1234567890-1 \
  --build-ref https://ci.example.invalid/runs/1234567890 \
  --artifact https://ci.example.invalid/runs/1234567890/artifacts/1 \
  --output ../run.json
```

```
Verification run: 3 result(s) to send from 1 feature(s); 5 left out.
  1 left out: not-in-baseline
  1 left out: revision-changed
  3 left out: no-result
```

The command reads every feature under `features/`, apart from starter features. It needs the target to be inside a Git repository that holds the baseline tag. It opens no connection and writes nothing in the target.

Sending the document is a separate step and is not part of this command yet.

## What you state

GovKit cannot observe these, so the caller gives them. Each is held to the rule the graph applies.

| Option | Meaning |
|---|---|
| `--baseline TAG` | The baseline tag the graph has indexed. Only a tag is accepted, not a branch or a commit |
| `--repository OWNER/NAME` | The repository as the graph knows it |
| `--run-reference SYSTEM:RUN-ID` | The run's own name in the graph. Lowercase system, then an identifier of up to 128 characters |
| `--build-ref REF` | The CI run's identifier or address |
| `--artifact URL` | An `https://` address of this run's report. The graph stores it and never fetches it |
| `--output FILE` | A new file outside the target. Without it the document goes to standard output |

The build commit and the execution time are not options. They come from the evidence record: the commit that was checked out, and the time the record was written straight after the tests.

## What the document holds

The document is `govkit.verification-run` (`governance/schemas/verification-run.schema.json`).

- **`request`** is the body the graph accepts, and the only part that may be sent. It holds the facts above and, for each result, the identifier, the revision digest, the kind (`test` or `evaluation`) and the outcome (`passed`, `failed`, `skipped` or `error`). It is null when no result can be sent.
- **`left_out`** lists what is not in the request, with a reason. An entry without an identifier covers a whole feature.
- **`features`** lists every feature that was read, with how many of its results are sent and left out.
- **`summary`** counts results and reasons.

The request holds no scenario title, file path, failure message or score. A failure's detail stays at the artifact link.

## Why a result is left out

The graph refuses a whole run when one result names a scenario or criterion that its baseline does not hold, or holds at another revision. GovKit therefore compares each result with the baseline tag in your checkout first. A result that would be refused is left out and listed, and the others are still sent.

| Reason | Meaning | What to do |
|---|---|---|
| `no-result` | The scenario or criterion has no result: it is missing or owed | Run the test or the evaluation |
| `not-in-baseline` | The baseline tag does not hold this scenario or criterion | It is new. It reaches the graph after the next baseline |
| `revision-changed` | The baseline holds it with different text | It was edited. It reaches the graph after the next baseline |
| `results-not-current` | The results are stale, unrecorded or cannot be checked | Run the tests and `govkit evidence --record` again |
| `tree-not-clean` | The results were recorded from a tree with uncommitted changes | Commit, then run the tests and record again |
| `skips-unmarked` | A result file counts skipped tests it does not mark, so a pass cannot be told from a skip | Make the runner mark skipped tests |
| `feature-unreadable` | The feature's report ended in an error before its results were checked | Run `govkit evidence --feature` for the detail |
| `baseline-unreadable` | The feature's files at the baseline cannot be identified, or are not regular files | Check the tagged files |

A criterion's revision is the digest of the whole `eval_criteria.yaml`. Editing any part of that file changes the revision of every criterion in it.

In the graph, a scenario that was left out shows as `unverified`, or as `stale` when an earlier revision has results.

## Exit status

| Status | Meaning |
|---|---|
| 0 | A request was built |
| 1 | Nothing can be sent. The document is still written, with `request` null |
| 2 | The run could not start: a stated fact was refused, the tag does not exist, or the output could not be written |

## Building twice

Two builds from the same record give the same document, because the commit and the time come from the record. The graph answers an identical re-send with the stored run, and a different run under the same reference with a conflict. A correction is a new run with a new reference.

## What this does not show

- **It is not proof that tests ran.** The request is a projection of result files that an evidence record ties to a commit. See [feature evidence report](EVIDENCE_REPORT.md).
- **The graph still decides.** GovKit reads the baseline from the tag in your checkout. What the graph indexed is its own record, and it may refuse the run.
- **Scores are not sent.** The graph's verification run contract version 1 holds outcomes only. A criterion is sent as passed or failed, without its measured value.
- **Data-form criteria are not sent.** They are not compared, as in the evidence report.
- **The limits are the graph's.** A run holds at most 5,000 results, and a commit must be a 40-character SHA-1 name. A run over either limit is refused with status 2.

The rules for the request are copied from `discovery-engine`. There is no published schema to validate against yet.

See [ADR 0031](../plans/decisions/0031-verification-run-document.md).
