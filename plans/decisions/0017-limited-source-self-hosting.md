# ADR 0017: Limited source self-hosting through existing conformance

Status: Accepted for implementation in I12; integration pending.

## Context

I08 and I11 are integrated. I10 supplies local catalog, runtime and evidence
components, but #147 still lacks protected-caller/path-coverage deployment
evidence. #149 asks GovKit to consume its model without installing its complete
consumer payload. The installer source and shipped consumer artifacts have
different development contracts.

## Decision

Track a minimal `.govkit/profile.yaml`, replayable resolution, empty pack lock,
source policy, command configuration and one recurring maintenance request.
Choose no packs or agent integration. Use existing profile, pack, pipeline,
conform and posture commands; add no execution engine or public CLI surface.

The always-applicable `source-validation` workflow requires the source checks
for every request. Command providers belong in workflow `additional_checks`:
top-level `required_checks` are resolved as executable pack requirements by the
pack resolver, while this repository intentionally selects no packs. This is a
representation choice, not a waiver of mandatory checks.

Run the existing profile-validation tests and a small new executable contract
for the source Tests workflow. Select command execution explicitly; use isolated
Python with `-B`, pytest importlib mode and its cache disabled. This prevents the
checks from modifying Git-visible inputs and lets the installed-wheel exercise
use the wheel's runtime rather than a source-tree import. The source test files
are still inspected project code and are not sandboxed by these flags.

Keep `provider:protected-caller` required without a local provider. Canonical
conformance and posture retain that unknown and the unmeasured architecture
contract. Successful local commands cannot establish protected CI enforcement,
semantic architecture conformance or an overall passing result. The existing
fast/e2e/wheel jobs remain broader delivery checks.

## Trust and bootstrap

Normal use requires a separately controlled snapshot of a reviewed policy
revision, an explicit base and an accepted request. A second directory alone is
not a trust boundary. The bootstrap demonstration can use the locally reviewed
proposed policy, clearly identified as local evidence pending integration.
Never represent that demonstration as protected PR admission.

The bundled request describes a recurring model-validation task; it is not a
template that may silently declare every PR to be low-impact maintenance.
Feature, LLM and security test controls show that the unchanged profile retains
additional requirements. Unselected capabilities remain unresolved.

## Consequences and validation

This increment updates source bootstrap guidance because self-hosting now
exists. Do not run blanket `govkit apply`, install consumer skills or require
consumer feature packages here. Keep source guidance outside the wheel payload.
Unknowns do not block demonstrating the local model, but #147 stays open and
#149 retains the I13 compatibility/warning/removal-boundary criterion.

Tests first establish missing metadata; real CLI tests then cover resolution,
catalog composition, execution opt-in, passing/failing source commands, actual
Git stability, trusted-policy separation, workflow escalation and canonical
posture. Installed-wheel and live source runs supplement those isolated tests.
The pipeline contract checks declared topology and selected commands; it does
not parse arbitrary shell semantics or authenticate a provider.

PR #198 review refinement: the source wheel smoke receives an explicit full
comparison SHA from the caller, with full-history checkout and the PR base/push
`before` event binding in CI. It refuses HEAD-as-base and unavailable inputs,
and verifies the canonical report contains exactly the captured comparison.
The Python matrix control verifies the setup-python interpreter binding as well
as the declared values. These improve measured coverage without changing the
candidate-policy or unknown-enforcement boundaries above.
