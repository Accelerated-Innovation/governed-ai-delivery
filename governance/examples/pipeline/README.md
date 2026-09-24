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
Provider rendering, protected generation and actual CI evidence are I10b.
