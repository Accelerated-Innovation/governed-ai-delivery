# Start with explicit capabilities

For a new adoption, inspect the repository, review its existing accepted sources,
and select the capabilities and controls the team needs. A profile records those
choices; packs install only their selected resources and skills. You do not need
level flags, the consumer architecture library, or a nine-step calibration before
using this path. Recording a profile does not execute controls or approve policy.

If the repository already has a legacy `.govkit/marker.json`, use
[legacy migration](LEGACY_MIGRATION.md) for a preview that preserves its configured
requirements, customizations and rollback. Do not replace that marker with this
example profile. Existing legacy commands remain supported; no removal release
or warning period has been announced.

## Try the commands in an isolated example

Install the CLI with Python 3.11+ using `python -m pip install govkit`. The examples
below require a build that includes `govkit profile` and `govkit pack`; check their
`--help` output first. Repository development installs use `python -m pip install
-e ".[test]"` from the source checkout. This guide is verified against the built
wheel from this implementation, not a claim that an unreleased change is on PyPI.

Use Bash for this recipe (including on Windows via a Bash environment). The CLI
itself supports other shells; this recipe does not establish Windows/deep-path
compatibility. Run the steps individually, stopping to review each preview.

```bash
GOVKIT_DEMO="$(mktemp -d)/service"
mkdir -p "$GOVKIT_DEMO"
GOVKIT_PROFILE="${GOVKIT_DEMO%/*}/proposed-profile.yaml"
GOVKIT_AGENT=codex       # claude-code, codex, or copilot
GOVKIT_CI=github         # github or azure; selection does not generate a pipeline
cat > "$GOVKIT_DEMO/policy.md" <<'POLICY'
Demo policy: evaluate the supplied greeting case. This is fixture policy only.
POLICY
```

### Inspect before selecting policy

<!-- example: discover -->
```bash
govkit discover --target "$GOVKIT_DEMO" --json
```

Discovery writes nothing. Its observations and proposed decisions are not accepted
architecture. In an existing service, reference the team's actual contracts and
make focused decisions about gaps. For an unfamiliar repository, leave its stack
unknown instead of imposing a framework. See [brownfield discovery](BROWNFIELD_DISCOVERY.md).

### Review a small profile

This synthetic example selects application guidance and an independent LLM
exact-match control, without Gherkin. The stack remains unknown. `accepted` is the
author's assertion about the referenced policy, not authenticated team approval.
For a real repository, review and replace the example's identity, policy reference,
capabilities, integrations and required controls before applying anything.

<!-- example: profile -->
```bash
cat > "$GOVKIT_PROFILE" <<EOF_PROFILE
schema_version: 1
source: {reference: policy.md, authority: accepted}
repository: {id: onboarding-demo, stack: null}
integrations:
  agent: ${GOVKIT_AGENT:-codex}
  ci: ${GOVKIT_CI:-github}
capabilities:
  - id: application-governance
  - id: llm-evaluation
policy:
  source: {reference: policy.md, authority: accepted}
  required_checks:
    - id: llm-exact-match
EOF_PROFILE
```

Preview both metadata and resources while the proposal is still outside the target:

<!-- example: profile-preview -->
```bash
govkit profile preview --profile "$GOVKIT_PROFILE" --target "$GOVKIT_DEMO"
```

<!-- example: pack-preview -->
```bash
govkit pack preview --profile "$GOVKIT_PROFILE" --target "$GOVKIT_DEMO"
```

These commands do not write to the project. Stop on unresolved decisions or
protected files. Review the selected pack versions, required checks and proposed
paths. A custom mandatory control needs an available executable provider; do not
remove a requirement simply to obtain a successful preview.

### Apply the reviewed selection

After accepting the proposal, save only the profile and generated resolution:

<!-- example: profile-apply -->
```bash
govkit profile apply --profile "$GOVKIT_PROFILE" --target "$GOVKIT_DEMO"
```

Then install the reviewed packs and verify their pinned contents:

<!-- example: pack-apply -->
```bash
govkit pack apply --target "$GOVKIT_DEMO"
```

<!-- example: pack-verify -->
```bash
govkit pack verify --target "$GOVKIT_DEMO"
```

The lock records the selected versions, content digests and ownership. Profile and
pack reapplication preserve unchanged bytes and modification times. Project-owned
files and modified installed skills remain protected. Do not delete a lock or use
legacy `--force` to bypass a protected pack operation. See
[capability packs](CAPABILITY_PACKS.md) for explicit pins and reviewed updates.

This profile installs the following skill directories, each containing `SKILL.md`.
Use the exact names; a `govkit-` prefix is present only where shown.

| Installed skill | Purpose |
|---|---|
| `application-governance` | Guidance for accepted application contracts |
| `govkit-request-planning` | Normalize a request for deterministic workflow planning |
| `llm-evaluation` | Guidance for the independent evaluation control |

| Agent | Native skill root |
|---|---|
| Claude Code | `.claude/skills/` |
| Codex | `.agents/skills/` |
| Copilot | `.github/skills/` |

The profile does not install the legacy spec-planning/preflight skill suite,
consumer architecture contracts, a legacy marker, `features/`, or CI workflows.
Guidance is not enforcement. Selecting a CI provider does not activate a gate.
Commit the reviewed profile, resolution, lock, pinned resources and native skill
copies together, after inspecting the actual diff.

### Run a control and prove it can fail

Create a synthetic record in the example target:

<!-- example: evaluation-input -->
```bash
cat > "$GOVKIT_DEMO/evaluation-results.json" <<'RESULTS'
{"cases":[{"id":"greeting","expected":"hello","actual":"hello"}]}
RESULTS
```

<!-- example: evaluate -->
```bash
govkit pack check --target "$GOVKIT_DEMO" llm-exact-match -- --results evaluation-results.json
```

The command runs independently of an agent session and exits 0 for this matching
fixture. Change `actual` to `wrong` and run the same command: it exits 1 and names
`greeting` in `failed`. Exit 2 means malformed input. Pack checks run trusted pinned
code and are not sandboxed. This evaluator compares supplied outputs; it does not
call a model, authenticate results, or establish broader model quality.

For canonical repository results use [conformance](CONFORMANCE.md), with explicit
execution opt-in and arguments. An unexecuted required control remains unsatisfied;
installation and `pack verify` do not constitute a passing evaluation. Fixture
results must not become project or release evidence.

## Move from the example to an actual change

- Use [declarative profiles](DECLARATIVE_PROFILES.md) to reference accepted sources,
  scope architecture transitions and retain mandatory controls. Exemplars are
  optional design aids, never inferred policy.
- Use [request workflows](REQUEST_WORKFLOWS.md) to plan a defect, small enhancement,
  refactor or full feature against one accepted profile. Independent Gherkin and
  LLM capabilities do not require each other. Only invoke skills actually installed.
- Use [actual-change conformance](CHANGE_CONFORMANCE.md) with an explicit comparison
  base and separately trusted policy; a task label cannot waive required checks.
- Preview [CI integrations](PIPELINE_GENERATION.md), then establish protected caller
  and path coverage separately. Static files are not proof of enforcement.
- Use [maintenance assessment](MAINTENANCE_ASSESSMENT.md) before a resource update,
  then verify its outcomes. Updating the developer CLI is separate from refreshing
  a repository's resources. Legacy migration has its own preview/digest/rollback
  procedure; this new-adoption recipe is not a migration shortcut.

Keep unknown architecture, freshness and provider evidence visible. The source
repository's own limited self-hosting is documented separately in
[plans/SOURCE_SELF_HOSTING.md](../plans/SOURCE_SELF_HOSTING.md); do not apply the
consumer example to GovKit itself.
