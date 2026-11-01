# SOAA Experiments

Advisory GovKit guidance for planning architecture experiments in a consuming
project. The contracts remain authoritative. These patterns are not a mandatory
suite: run an experiment only for a material uncertainty.

## When preflight says experiment-required

Set the preflight outcome to `experiment-required` when the design depends on
an untested assumption about ownership, authority, activation, effects,
recovery or completion. Do not label an unproven design aligned to begin a
contained prototype. A known violation of an accepted boundary still needs an
authorized change or a narrower experiment. An ordinary change inside a tested
boundary takes the short path, without an experiment.

## Patterns

Each experiment adds one hypothesis and one bounded capability. Run positive,
negative and fault cases against the actual adapter. Keep most control tests
deterministic. Run the real model-facing adapter before claiming model-driven
behavior.

| Experiment | Hypothesis and scope | Evidence required before expansion |
|---|---|---|
| E1 | Control skeleton: one adaptive task preserves ownership, authority, activation and completion with modest effort | Accepted and rejected offers; exact binding; denied model writes; labeled context; blocked false success; finite budgets; restart and reconstruction |
| E1b | Skill choice (part of E1): a small set of skills can be selected appropriately without weakening activation controls | Held-out selection, null and ambiguity cases; eligibility and release-state rejection; task outcome, latency and cost |
| E2 | Controlled mutation: a lost acknowledgment does not duplicate effects or create false terminal success | Intent before effect; stable operation ID; crashes before and after the effect; reconciliation; cancellation; late results; retry and recovery budgets |
| E3 | Sequential skills: a versioned workflow switches skills without stale authority or instructions | Atomic transition; context replacement; delayed old calls rejected; version conflicts; crash and restart; failed activation leaves consistent state |
| E4 | Targeted extension: a needed feature does not import unrelated obligations | Choose ranking, memory or retrieval, multi-tenant use or takeover separately; run the relevant applicability cases and the common invariants |
| E5 | Delegation or portability: a product need justifies cross-owner or cross-runtime complexity | Child acceptance, authority attenuation, transfer and joins, remote false completion, or independently implemented differential behavior |

Use the `catalog/gk-soaa-cases.yaml` cases whose conditions apply. They are
GovKit local cases, not SOAA assertions.

## Stopping conditions

- Do not enable mutation beyond a fixture until E2 demonstrates the failure
  semantics. A timeout does not mean rollback.
- Unreconcilable effects stop new unsafe work and stay unknown for an
  authorized operator. Compensation is a new authorized operation.
- Do not finalize success while a required effect or evidence outcome is
  unresolved.
- Halt expansion when a counterexample breaks ownership, authority, evidence or
  completion, or when the control burden is unjustified for the consequence.
  Revise the control or narrow the supported behavior; do not weaken tests to
  keep a label.

## Mapping to `experiments.yaml`

Record each experiment in `features/<feature>/experiments.yaml` (schema
`experiment-set` v1).

| Pattern element | `experiments.yaml` field |
|---|---|
| Material uncertainty | `uncertainty` |
| Hypothesis | `hypothesis` |
| Preflight decision or contract it informs | `decisions_affected` |
| Accepted requirements that must stay intact | `requirements` (with digests) |
| Bounded capability and permitted effects | `scope.paths`, `scope.permitted_effects`, `scope.excluded` |
| Test conditions | `conditions` |
| Oracle | `oracle` |
| Evidence required before expansion | `acceptance_criteria` (cite GK-SOAA case IDs in `refs`) |
| Stopping conditions and budget | `limits.stop_when`, `limits.budget` |
| Runtime, skill, policy and adapter files | `depends_on` (with digests) |
| Synthetic fixture or application run | `required_evidence_class` |

A passing experiment supports only its observed scope. Feature completion
still checks every applicable accepted requirement and control. A changed
requirement, dependency or result invalidates the affected evidence.

## Illustrative example (unverified)

A discovery assistant leads a team through discovery with 2–3 skills. Those
skills do not by themselves make it multi-agent. A first slice might pick one
real discovery task and one skill, and run E1 with synthetic data and a
reversible local effect. A second slice adds E1b once it is clear whether a
person, a trusted workflow or the model chooses among the skills. A later
transition to a different skill set would use E3.

This example is illustrative only. No such application has been inspected,
executed or verified by GovKit, and the example establishes no runtime
behavior.
