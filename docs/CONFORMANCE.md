# Local check and evidence reports

`govkit conform` collects profile, installed-resource and legacy check results in a shared report. It preserves required controls even when their provider or evidence is missing. This is the I04 check foundation: it does not yet select a workflow from a request/diff, enforce architecture transitions, generate pipelines, or assess release freshness and maintenance.

```sh
govkit conform --target ./service
govkit conform --target ./service --json > check-results.json
```

Inspection is offline and read-only. The command prints its report; shell redirection writes the chosen output file. Legacy `.govkit` marker files are read without migrating them. Run once per explicit project target; this command does not discover monorepo projects automatically. Existing `doctor`, `validate`, `extension` and `evidence` commands retain their output and exit behavior.

## Controls and execution

| Check ID | Assessed scope and limits |
|---|---|
| `govkit:profile` | Profile validity and available resolution metadata consistency; cannot authenticate the accepted policy reference |
| `govkit:pack-lock` | Replayed pinned resources and native skill copies; does not execute controls |
| `legacy:doctor` | Existing governance-fit findings; clean heuristics remain unknown because their empty fallbacks cannot establish coverage |
| `legacy:features` | Existing legacy feature artifact checks; local schema validation is offline, self-predictions remain assertions, no application tests run |
| `legacy:extensions` | Legacy extension manifests and referenced paths; does not establish contract compliance |
| `legacy:approval-policy` | Local policy/ADR attestation structure; cannot authenticate reviews or prove a CI gate is active |
| Pack check IDs | Pinned Python entry points; configured controls stay skipped until explicitly executed |

The profile's accepted `policy.required_checks` are always selected and retain their policy reference. A missing provider reports unknown. Pack-declared required checks also remain required. The foundation evaluates these requirements across the explicit project target; conditional change/workflow applicability comes later. It provides no caller filter to remove mandatory controls.

To execute an installed control, opt in by ID and supply its arguments:

```json
{"llm-exact-match": ["--results", "results.json"]}
```

Save that mapping as `check-arguments.json`, then run:

```sh
govkit conform --target ./service --json \
  --execute-pack-check llm-exact-match \
  --pack-arguments check-arguments.json
```

The arguments file is relative to the invoking shell; control arguments are passed unchanged and the control runs in the target directory. Repeat `--execute-pack-check` for multiple controls. This executes explicitly trusted pinned code and is not a sandbox; custom code can have side effects. Pack controls run independently of loading an agent skill. A missing native copy still produces a separate installation finding. The bundled exact-match evaluator measures supplied case outputs: it does not invoke a model or authenticate how those outputs were produced.

## States, totals and exit status

Execution (`not-run`, `executed`, `error`) is separate from the outcome (`pass`, `fail`, `warn`, `unknown`, `skipped`, `not-applicable`, `waived`). A pass requires an executed result with evidence from a local check or tool execution. Agent assertions and unverified artifacts cannot independently establish a pass. Missing or unreadable inputs, unavailable schema coverage, exceptions and invalid check results stay visible. One broken check does not suppress unrelated results.

Only `pass` counts in `required_satisfied`. Every required check contributes to the `required` denominator, including unknown, skipped, not-applicable and waived entries. This foundation represents waived state but has no waiver authorization engine; it cannot satisfy a required check. State counts include both required and advisory checks; `executed` counts checks attempted successfully enough to return a result, including failures. A protocol error has execution `error` and is excluded from that count.

Exit **1** means at least one failure, an unsatisfied required check, or no passing checks at all. Exit **0** means the named required checks passed and there are no failures; advisory uncertainty may still yield an overall `warn`. Any failure makes the overall state `fail`; otherwise blocked/inconclusive runs are `unknown`. This exit status does not certify the whole repository or authenticate policy/evidence.

## Raw result contract

The versioned [check-results schema](../governance/schemas/check-results.schema.json) covers identities, applicability reasons, policy sources, findings, execution states, evidence and aggregate counts. Findings carry stable IDs derived from the check ID, finding code, location, scope and message. Identical explicit inputs serialize deterministically; changed observations/messages can change IDs. Feature adapter codes `feature-00` onward follow the established legacy check order.

The repository ID comes from a valid profile, otherwise the target folder name. Profile, available resolution and lock digests are included. `--revision` and `--observed-at` are optional caller annotations, not independently verified facts. Unavailable revision, dirty-tree, actual-change and time identity remain null; the command does not infer them from environment variables or Git.

Evidence names source, scope, method, origin, digest when available, and limitations. Digests establish content consistency, not authenticity or complete execution coverage. JSON includes check messages and repository-relative artifact/policy paths; legacy messages can contain content-derived details. Inspect a report before sharing it. No automatic transmission occurs. Captured pack stdout/stderr and argument values are hashed rather than copied into the report, and unexpected exception payloads are omitted.

Worked reports demonstrate [a structural profile pass](../governance/examples/check-results/profile-pass.json), [an unconfigured required control](../governance/examples/check-results/required-unknown.json), and [a real exact-match failure](../governance/examples/check-results/evaluation-fail.json). They use synthetic repository/revision annotations and temporary consumer fixtures. A profile pass alone says nothing about unselected application controls.

`cli.check_runner.load_report` validates schema, canonical finding identities and recomputed totals for inspection. It does not authenticate a report or accept it as gate evidence. Run the checks again against the relevant inputs. Local and CI callers can use the same engine; the wheel smoke test demonstrates parity for the same explicit fixtures. Provider evidence, actual-change routing and enforcement parity remain later work.
