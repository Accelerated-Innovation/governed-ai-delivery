# ADR 0007: actual-change conformance and trusted policy

Status: accepted for I07 implementation.

I06 produces a deterministic plan from explicit observations; author-controlled
labels or a supplied path list cannot establish actual change conformance. I07
captures Git base/current inputs and recomputes I06 requirements against a separate
caller-controlled accepted policy checkout. It adds required scope, policy, plan,
architecture, artifact and stability checks through I04's registry, keeping legacy
repository inspection and commands compatible.

The new optional profile `policy.conformance` source binds configuration bytes into
plan evidence. Configuration maps literal paths to additive impacts, artifact
references, literal boundary measurements and explicit command providers. This
small provider contract makes executable behavior reviewable without interpreting
arbitrary prose as a rule. Missing coverage is unknown. Existing required/pinned
checks survive routing even when their related files are unedited.

The separate checkout is a trust boundary, not an authentication mechanism. CI must
choose accepted inputs independently from the change. Captured content and final
recapture detect ordinary stale or changing inputs; they do not offer atomic
filesystem snapshots or a sandbox. Commands are opt-in, trusted and unsandboxed.
Local code cannot approve architecture or grant arbitrary waivers. Scoped, dated
existing exceptions apply only to baseline occurrence counts; target applicability
is separate. Built-in architecture measurement is deliberately literal, with
unmeasured semantic dimensions stated in evidence.

Defects reuse existing eligibility with a bundled-schema validation boundary;
legacy validation keeps its existing default. Opted-in baseline/current execution
runs in a temporary copy and current target, never a destructive checkout. These
outcomes prove only the configured tests. The outer change-results contract embeds
and replays the I06 plan and I04 report, retains identities/provenance and provides
the same entry point locally and in CI. It is not an authenticated gate artifact.

See [the command guide](../../docs/CHANGE_CONFORMANCE.md) for exact inputs, bounds,
limitations and seven executable pilot fixtures. Migration, maintenance and provider
integration remain I08–I10. No consumer assets are applied to the GovKit source repo.
