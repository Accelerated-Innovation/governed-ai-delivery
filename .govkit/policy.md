# GovKit source self-hosting policy

This is the explicit minimal source policy for I12 of
`plans/declarative-governance-implementation-plan.md` and issue #149. The source
repository builds the installer and consumer payload. Its own profile selects
no capability packs, agent integration, native skills or consumer architecture
documents. The empty lock pins that deliberate selection. There is no legacy
marker and no source feature-package workflow. Do not run `govkit apply` here.

The recurring source-maintenance request verifies this chosen model. It is not
the implementation request for every PR and must not relabel feature, security,
public-contract, LLM or architecture changes as bounded maintenance. Those
requests retain their actual impacts, test-first evidence and issue/plan review.

The following controls are required throughout the source tree:

- `project:tests` executes `tests/test_profiles.py`, the bounded regression suite
  for profile validation, accepted authority and deterministic resolution. It
  requires the development test dependencies. A pass covers that suite only.
- `project:pipeline-contract` executes `tests/test_source_pipeline_contract.py`.
  It checks the source Tests workflow's main-branch push/PR event coverage,
  unconditional jobs/steps, Python matrix, complementary tier declarations,
  e2e pipeline error propagation and wheel job ordering/build declarations.
  It does not interpret arbitrary shell code or prove hosted execution.
- `provider:protected-caller` has no local provider. It remains required and
  unknown until protected-caller deployment/path-coverage evidence is accepted
  under #147. Do not waive it or fabricate a command that always passes.

The existing fast, e2e/toolchain and installed-wheel CI jobs remain the broader
delivery checks. Local conformance does not certify branch protection, review
approval, live CI activation, every architecture boundary or release currency.
In particular, the source contract above documents installer/payload separation;
there is no semantic architecture provider configured for that contract yet.

Commands execute only with explicit opt-in against the inspected source tree.
Select the policy from a separately controlled, reviewed checkout and choose the
request and full base SHA explicitly. Copying candidate policy into another
directory does not authenticate it. Bootstrap demonstration results are local
evidence, not protected PR admission. Posture exports preserve canonical states
and execution, including unknowns, and carry unauthenticated snapshot provenance.
Publish only on explicit request outside both checkouts.
