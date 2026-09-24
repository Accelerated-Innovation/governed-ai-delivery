# ADR 0012: Prepared-input provider entry points and protected generation

Status: accepted for I10b, 2026-09-24.

I10b emits reusable GitHub composite actions and Azure step templates. They call
one common engine after verifying exact runtime/profile/pack bindings, without
owning checkout, credential acquisition, event admission or external enforcement.
I10c retains those provider authority/evidence integrations and maintenance facts.
Every original #147 criterion remains required across the split.

Callers explicitly provision an isolated pinned runtime, complete inspected Git
checkout, independent trusted policy/pack checkout, accepted request and full base
SHA. Inputs cross the provider boundary as environment values, never inline shell
expressions. Absolute interpreter validation and `exec --` prevent interpreter
options from becoming successful shell built-ins. Python isolation excludes the
inspected checkout from import resolution. No package/network installation occurs.

The common runtime validates the installed GovKit version, accepted profile digest
and replayed pack closure before invoking existing actual-change conformance.
Execution opt-ins are concrete settings; unknown/disabled required checks do not
pass. Pin equality is consistency, not release authenticity or event authority.
The caller must trust the interpreter/build and reusable template revision.

Generation owns only one fixed provider path and a replayable metadata record.
Preview exposes exact content and binds source bytes, target location and prior
destination bytes/modes/timestamps in its authorization digest. Generate requires
that exact current digest, reloads packs/inputs and checks again after staging.
Unknown files, user edits and invalid metadata remain protected; provider switches
require explicit reconciliation. No force overwrite or automatic workflow rewrite
is added. Caught failures roll back files and ordinary metadata; concurrent edits
and process crashes remain outside transactional guarantees.

Check reports configuration separately from unknown activation/execution/enforcement.
Golden provider contracts and real local script pilots establish equivalent common
engine behavior; no hosted provider or maintenance integration is inferred from
YAML presence. Public schemas, guide, examples and installed-wheel CI pilots track
this boundary. Source-repository self-hosting remains I12.
