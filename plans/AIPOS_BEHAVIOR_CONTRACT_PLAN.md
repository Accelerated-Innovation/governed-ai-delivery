# AIPOS Behavior Contract — this repository's scope

Increment 00 record, 2026-09-17. **Design record, not an approval.**

The canonical cross-repository policy, ownership table, authority mapping, and interface
decisions live in the AIPOS operating-model record
*AIPOS-Behavior-Contract-Repository-Contract.md*. This file holds only what govkit's source
repository decides for itself. Peers: `docs/plans/2026-09-17-aipos-behavior-contract.md` in
govkit-plugins, and `ADR-AIG-029` in discovery-engine.

## What AIPOS asks of govkit

An AIPOS product commitment is a **versioned behavioral baseline**: exactly which Rules,
scenarios, constraints, NFRs, evaluations, and agent authority were approved, bound to immutable
source revisions. govkit owns the portable contract for that baseline, the local validators that
check a working tree against it, the client that asks the Opportunity Engine whether the
approval still authorizes work, and the installed payload — agents and CI — that makes the
boundary real in a target project.

## This repo is the installer, not a governed application

`CLAUDE.md` is unchanged by this work and still governs: no `features/` workflow, no
`/govkit-*` skills, no `.govkit/` marker govern development here. So:

- **No feature package is created for this work.** It is planned here, in `plans/`, like every
  other cross-cutting change in this tree.
- `features/` in this repository remains distributed starters and examples. AIPOS does not turn
  it into a governance workflow for govkit's own development.
- The split that drives every task still applies. Increment 01's schema, the fixtures, the
  agent instructions and the CI templates are **payload**. The validator module, its `validate`
  and `doctor` integration, and the engine-status client are **installer**.

## Increments owned here

| Increment | Deliverable | Layer |
|---|---|---|
| 01 | `governance/schemas/behavioral_baseline.schema.json`, the digest rule, golden vectors, valid/invalid fixtures | payload + tests |
| 10 | Local baseline/reference validation and the structured difference report; `validate`/`doctor` integration | installer |
| 11 | A bounded engine-status client: exact decision id, baseline digest, opportunity/scope binding, current revision | installer |
| 12 | `agents/{claude-code,codex,copilot}` instructions to load the baseline before planning and to route scope change to a decision | payload, three agents in lockstep |
| 13 | `ci/github/` and `ci/azure/` gates, installation manifests, CI docs | payload, two CI systems in parity |
| 15 | Packaging, managed-file protection, agent and CI parity, the explicit AIPOS activation, and the conversion path for existing packages | both |

## Decisions taken now

**Schema location and identity.** `governance/schemas/behavioral_baseline.schema.json`, with
`$id: urn:governed-ai-delivery:schemas:behavioral_baseline`, matching
`approval_policy.schema.json`. Area-agnostic, so it sits in `governance/schemas/` rather than
`governance/<area>/schemas/` — a baseline has the same shape for api, cli, ui and data.

**Versioning.** An integer `version` in the instance, as `approval_policy.yaml` does. The
validator holds an explicit list of supported versions and fails an unsupported one with a
named error, never a schema-shaped one.

**Packaging.** `governance` is already in `[tool.hatch.build.targets.wheel.force-include]`, so
the schema ships with no packaging change. **A new fixture directory does not** — adding one
requires its own `force-include` entry and a wheel test, per the standing rule that
editable-install tests can pass while the wheel is broken.

**Validator posture — read-only.** It never rewrites a spec to make it pass, never adds a
missing ID during enforcement, and never silently upgrades a manifest. This mirrors
`cli/approval.py`'s existing split: **validate proves internal consistency; CI proves
correspondence with reality.** The baseline validator proves artifact consistency; only the
engine status read proves authority.

**Three separate things, never merged into one check:**
1. deterministic local consistency (the validator),
2. authenticated authority (the engine status read),
3. advisory AI analysis (labelled advisory *in the data*, not only in prose).

**CLI conventions, unchanged.** Any new exposed command gets its own `cmd_*.py` with
`register(subparsers)` wired through `_REGISTRARS`; command modules import no other command
module; `cli/paths.py` stays dependency-free and is referenced at call time.

**Authority vocabulary is reused, not reinvented.** The reviewer / approver / human-execution-
owner / accountable-principal roles and the prohibited-pattern list in
`extensions/skill-oriented-agent-architecture/docs/backend/architecture/AUTHORITY_AND_APPROVAL_CONTRACT.md`
carry over verbatim. Three prohibited patterns bind increments 11 and 13 directly: reusing stale
activation authority for a later operation; approval by an unauthorized identity; treating chat
acknowledgment or authentication as approval.

**ADR approval is not product approval.** `cli/approval.py` and `governance/approval_policy.yaml`
answer "may this identity accept an ADR in this repository". An AIPOS product commitment is a
different decision, decided elsewhere, by an identity holding a different scope. The two
mechanisms stay separate; neither is extended to stand in for the other.

**Adoption is explicit.** AIPOS enforcement is opted into. It is not inferred from an existing
GovKit adoption level, and GovKit adoption levels L3/L4/L5 are never equated with AIPOS workflow
detail levels L1/L2/L3 — different vocabularies, and no code or doc may conflate them. A generic
or legacy installation keeps working with no baseline, no authority check, and no new gate.

**Parity is not optional.** Increment 12 changes `agents/claude-code`, `agents/codex` and
`agents/copilot` together with byte-identical skill frontmatter; increment 13 changes
`ci/github/` and `ci/azure/` together with `ci/README.md`. Both are enforced by the existing
suites (`pytest -k parity`, `tests/test_agent_skills.py`, `tests/test_govkit.py`).

**CI gate trust.** The gate runs trusted code and configuration from the protected branch, not a
pull request's replacement validator holding credentials. A PR cannot disable enforcement,
substitute an approval endpoint, or weaken policy to approve itself. Where the hosting setup
cannot perform a fresh authoritative check at the merge boundary, increment 13 **reports that
limitation and the required host integration** rather than claiming the problem is solved.

## Verification posture

Per-increment, using the suites that already exist beside the code being changed:

```sh
pip install -e ".[test]"
./run_tests                                        # fast loop during development
pytest tests/test_schemas.py tests/test_fixtures.py   # increment 01
pytest tests/test_agent_skills.py tests/test_govkit.py -k parity   # increment 12
ruff check <changed files> && ruff format <changed files>          # never a dir-wide run; fix=true rewrites
```

Every changed schema example and starter is validated against its declared schema. A fake-based
suite is never reported as evidence of real integration, and a skipped or blocked check is never
reported as passed.

## Status

Nothing in this file is implemented. No schema, validator, client, agent change, or CI gate
exists yet. No approval, release, or publication is authorized by writing it.
