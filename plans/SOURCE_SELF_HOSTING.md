# Limited source self-hosting

GovKit's source uses an explicit, deliberately small [profile](../.govkit/profile.yaml)
and [policy](../.govkit/policy.md). No consumer packs, architecture documents,
agent skills or legacy marker are installed. `features/` remains shipped payload.
Do not run `govkit apply` against this repository.

The source policy requires two executable controls and one unmeasured control:

| Control | What it measures |
|---|---|
| `project:tests` | The existing `tests/test_profiles.py` regression suite: 31 current cases for profile validation, accepted authority and deterministic resolution |
| `project:pipeline-contract` | Eight assertions against `.github/workflows/test.yml`: main push/PR path coverage, unconditional jobs/steps, Python matrix, fast/e2e tier declarations, e2e error propagation, wheel dependencies/build declarations |
| `provider:protected-caller` | Required, unknown, not run: protected-caller/path-coverage evidence remains #147 |

The prose architecture contract also remains unknown without a configured
semantic/literal provider. A conformance run therefore has a nonzero exit even
when both executable controls pass. Exporting posture can succeed while its
canonical conformance outcome remains unknown. Neither result proves live CI
activation, branch protection, release currency or full-suite success. The
existing fast, e2e/toolchain and installed-wheel jobs remain required delivery
validation outside this bounded local demonstration.

## Resolve and inspect

Install the development dependencies with `python -m pip install -e '.[test]'`.
These project checks need pytest; it is not a GovKit runtime dependency.

```sh
govkit profile preview --target . --json
govkit pack verify --target . --json
govkit pipeline catalog --target . --json
```

All three commands are read-only. Catalog readiness means the declarations
resolve; execution stays `not-run` and enforcement stays `unknown`.

## Execute with separately selected policy

Choose a reviewed full policy commit in `GOVKIT_POLICY_REV` and the full Git
comparison SHA in `GOVKIT_BASE`. Use an absolute development interpreter path
in `GOVKIT_PYTHON`. The policy revision must contain this source profile. For
bootstrap validation before integration, explicitly review the candidate policy
and label the resulting evidence as local proposed-policy demonstration.
Copying a candidate's policy to a second directory does not authenticate it.

The following Bash example creates private records outside the source tree.
The recurring request validates the chosen model; it does **not** represent the
implementation intent/impact of every PR. Use an appropriate accepted request
for feature, security, API, LLM or architecture work.

```bash
set -euo pipefail
: "${GOVKIT_POLICY_REV:?Set a reviewed full policy commit SHA}"
: "${GOVKIT_BASE:?Set the full comparison base SHA}"
: "${GOVKIT_PYTHON:?Set an absolute Python path with GovKit and test dependencies}"
umask 077
GOVKIT_EVIDENCE=$(mktemp -d "${TMPDIR:-/tmp}/govkit-source.XXXXXX")
mkdir "$GOVKIT_EVIDENCE/policy"
git archive "$GOVKIT_POLICY_REV" .govkit | tar -x -C "$GOVKIT_EVIDENCE/policy"
GOVKIT_OBSERVED_AT=$("$GOVKIT_PYTHON" -c 'from datetime import datetime, timezone; print(datetime.now(timezone.utc).isoformat())')

conformance_status=0
"$GOVKIT_PYTHON" -I -B -m cli.govkit conform \
  --target "$PWD" \
  --policy-target "$GOVKIT_EVIDENCE/policy" \
  --request "$GOVKIT_EVIDENCE/policy/.govkit/requests/source-maintenance.json" \
  --base "$GOVKIT_BASE" --observed-at "$GOVKIT_OBSERVED_AT" \
  --execute-check project:tests --execute-check project:pipeline-contract --json \
  > "$GOVKIT_EVIDENCE/change.json" || conformance_status=$?
printf 'Conformance exit status: %s (inspect the canonical results)\n' "$conformance_status"

"$GOVKIT_PYTHON" -I -B -m cli.govkit posture change \
  --results "$GOVKIT_EVIDENCE/change.json" --json \
  > "$GOVKIT_EVIDENCE/posture.json"
"$GOVKIT_PYTHON" -I -B -m cli.govkit posture change \
  --results "$GOVKIT_EVIDENCE/change.json"
printf 'Private local records: %s\n' "$GOVKIT_EVIDENCE"
```

The nonzero status is recorded, not converted into a conformance pass. An invalid
or absent result fails posture replay. Inspect the local JSON for actual check
IDs, outcomes, command evidence digests, base/revision, tree and policy identity.
Posture pseudonymizes identifiers, preserves recorded execution/unknown states,
and labels provider enforcement `not-supplied`. Nothing is uploaded.

Commands run project-controlled Python tests with the selected interpreter and
are not sandboxed. `-I -B`, importlib mode and disabling pytest's cache avoid
source shadowing and bytecode/cache writes during inspection. Concurrent edits
invalidate the evidence; rerun after finishing edits.

## Maintain the small selection

After an explicitly reviewed profile change, `govkit profile preview` and
`govkit pack preview` show metadata/resource operations. Reconcile the two
generated files using the respective `profile apply` and `pack apply` commands
only after checking that the selection still contains no packs or owned payload
files. Commit `.govkit/resolution.json` and `.govkit/pack-lock.json` alongside the
profile. This scoped metadata operation is distinct from legacy `govkit apply`.
Conformance configuration/policy text are reviewed source files, not generated
consumer docs. Never delete the required unknown to obtain a green report.

For installed-wheel verification, install a newly built wheel and pytest into
a fresh environment. Run the same commands with that environment's absolute
Python path, checking `cli.__file__` under `sys.prefix` in isolated mode first.
Keep the existing runtime-only consumer wheel pilots separate: source test
dependencies must not become mandatory consumer runtime dependencies.

The Tests workflow's wheel job runs `tests/wheel_source_self_hosting_smoke.py`
in this separate environment. It checks that the two selected commands pass
and that canonical conformance remains unknown for exactly the unmeasured
architecture and protected-caller controls. The smoke's success means those
assertions held; it does not turn the underlying conformance result into a pass.

See [ADR 0017](decisions/0017-limited-source-self-hosting.md) and the
[I12 execution record](declarative-governance-implementation-plan.md#i12-execution-record--2026-09-24)
for scope, test-first evidence and remaining rollout work.
