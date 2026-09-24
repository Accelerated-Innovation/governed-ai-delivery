# Shared gate catalog example

Run `govkit pipeline catalog --profile profile.json --json` from this directory.
The example declares application governance and LLM evaluation independently of
Gherkin delivery. Change the accepted provider to `azure` to see the same logical
gate declarations. The example is a schema/selection fixture, not team approval.

The policy requires application governance and names LLM evaluation as a check
prerequisite. Both declarations and the policy source survive in the catalog;
removing a required capability produces unresolved decisions, not a silent waiver.

The result records the common conformance invocation, selected pack check,
composition version pins and unresolved configuration limits. It executes nothing,
generates no workflow and claims no enforcement. The catalog's command placeholders
describe the common-engine boundary; they are not a ready-to-run shell script.

The runtime-only wheel pilot runs application-only, application-plus-LLM and
Gherkin-only profiles for all three agents and both providers, plus an unresolved
capability control. It also verifies every frozen legacy install selection.
`settings.json` leaves executable checks disabled until explicitly accepted.
`github-entrypoint.yml` and `azure-entrypoint.yml` are paired golden examples for
this exact fixture profile and settings. Regenerate for a real accepted profile;
their bindings are not portable team policy. See [protected pipeline generation](../../../docs/PIPELINE_GENERATION.md).

The additional provider wheel pilot generates both integrations and runs their
actual scripts for all agents, bounded/full-feature/LLM requests and a failing
evaluation. I10c adds `*-admission-settings.json`, native `*-event.json`,
`*-admitted-entrypoint.yml` goldens and strict `*-observation.json` records. All
observation enforcement facts start as null: these examples are not live CI proof.
The provider evidence pilot admits clean source/policy commits and accepted request
bytes, checks canonical maintenance parity, and keeps missing or unauthenticated
exports unknown even when every supplied enforcement value is true. Explicit
failures survive mismatched runtime reports; no-lock CLI upgrades use available
pack snapshots only for a read-only proposal.
See [provider evidence](../../../docs/PROVIDER_EVIDENCE.md) for collection authority,
explicit publication, optional metadata refresh and protected upgrade previews.
