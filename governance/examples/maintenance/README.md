# Illustrative maintenance inputs

These fixtures describe a hypothetical team-approved static release feed. The
`.invalid` URL and newer versions are examples, not claims of published releases.
Use the fixed `2026-09-24T12:00:00Z` assessment time to demonstrate fresh selection;
real later assessments correctly report this fixture as stale. Refresh is disabled.

The installed-wheel pilot loads this profile and metadata, then stages an explicit
local candidate from the shipped Application Governance pack. Metadata itself does
not fetch or install that candidate. The profile is an example, not accepted policy
for this source repository.

For consolidated maintenance, pass the same metadata to `govkit maintain assess`
with the fixed time. An explicit last-reviewed discovery baseline lets an added
LLM import produce capability review while a customized native skill produces
resource reconciliation. Neither observation automatically accepts policy or
demands a CLI upgrade. A configured CI integration without a matching provider
check report stays unknown.

See [the assessment guide](../../../docs/MAINTENANCE_ASSESSMENT.md) for saved-record
preview/verification commands. `tests/wheel_maintenance_assessment_smoke.py` runs
this scenario for all three agents with synthetic CI pass/fail inputs, protected
upgrade previews and an actual resource repair. These are illustrative local
pilots, not claims of live CI or publisher verification.
