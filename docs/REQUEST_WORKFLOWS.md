# Proportional request workflows

A single accepted profile can serve a defect, bounded enhancement, refactor, substantial feature or architecture migration. `govkit request` keeps normalized intent local and selects obligations from impact, accepted policy and verified pinned capabilities. It never executes checks, installs resources, writes a tracker, downloads packs or reconfigures a repository.

## Start with local intent

```sh
govkit request template > request.json
# Edit and review the proposed record with its owner.
govkit request plan request.json --target .
govkit request plan request.json --target . --explain
govkit request plan request.json --target . --json > request-plan.json
```

The CLI prints to stdout; redirection is an explicit caller write. Planning requires the local accepted `.govkit/profile.yaml` and a verified `.govkit/pack-lock.json`. Use the existing profile/pack preview and apply commands for authorized setup. The Application Governance pack includes the agent-neutral `govkit-request-planning` skill, installed under that name for Codex, Claude Code and Copilot. Existing locks remain pinned until explicitly reconciled. Plans only name native guidance from the same lock snapshot whose pinned bytes and current profile were verified. The captured profile must match that snapshot; a concurrent profile change requires re-planning. This is an observation, not a filesystem transaction.

The request records `id`, original `source`, local `summary`, `confirmation`, change intent, literal repository-relative `scope`, impacts, acceptance, local references and an optional workflow preference. It can be JSON or YAML. The source identifier may be a ticket URL; no live lookup occurs. Preserve the current request and plan in the project's reviewed change process so later CI can inspect agreed intent offline.

`template` starts with proposed intent and unknown (`null`) impacts. The agent can draft normalization by reading the request, accepted contracts and affected code; unresolved material facts remain unknown. The owner confirms the normalized intent. Confirmation and authority fields are caller assertions, not authenticated approval. Neither an editable label nor line count waives controls.

Impact fields are `bounded`, `within-contracts`, `new-behavior`, `security`, `auth`, `data`, `public-contract`, `nfr`, `ownership`, `architecture`, `cross-service`, `llm` and `mcp`. Every normalized field must be explicit; unknown impacts retain applicable controls and block planning readiness. Scope paths are literal directories/files, not glob expressions. A request permits 64 paths and supplied observations permit 256; the resulting plan and each check retain their union of up to 320 distinct paths.

## Selected workflows

| Workflow | Eligibility and evidence |
| --- | --- |
| Defect | Restore accepted established behavior, with an existing local regression-test reference, bounded scope, no new behavior or sensitive impacts. Preserve the existing fix record and eligibility check, including actual red/green evidence. Merely finding the test file does not prove it ran. |
| Bounded | Enhancement, refactor or maintenance within accepted contracts covering every requested path, with explicit bounded scope and no sensitive impacts. Keep one compact change record and actual test evidence; a new bounded behavior does not itself demand five documents. Refactor/maintenance must preserve behavior. |
| Full feature | Substantial feature, wider/sensitive work or accepted policy requiring Gherkin delivery. Select spec, plan, architecture preflight, test plan and validation artifacts. |
| Architecture | Deliberate architecture change. Retain relevant controls, an accepted architecture decision and a transition plan covering current/target rules, scoped exceptions and exit verification. The plan grants no architecture approval. |

Checks include accepted unconditional repository controls, matched policy workflow checks, required pinned-pack controls, project tests and applicable impact reviews. Sensitive changes retain their controls even if the author prefers bounded work. Policy requirements accumulate; a policy requiring full delivery activates its further rules regardless of declaration order. Supported selectors are `*`, workflow/change identifiers, impact identifiers and the aliases `bounded-defect`, `small-change`, `substantial-feature`, `model-behavior`. Unknown selectors produce a blocking decision and retain that rule's requirements. `when` alternatives match with OR semantics. `bounded` denotes the bounded lane; unknown impacts conservatively match their conditions.

LLM impact requires the independent `llm-evaluation` capability and its pinned evaluations; it does not itself select Gherkin. Selecting a pack with a required check keeps that check required even for other requests. Missing capabilities produce explicit setup decisions and are never installed by planning.

## References, replay and changed scope

Acceptance can be recorded inline or reused through an accepted local reference. References have `kind` (`acceptance`, `nfr`, `contract`, `established-behavior`, `regression-test`), `reference`, `authority`, and an optional content `digest`. Files are read within the target, without symlink traversal, up to 64 KiB each. Missing or changed sources used by the plan are unresolved; an unavailable unrelated contract is informational. Source digests record observations, not authenticated authority or passing evidence.

The versioned plan includes normalized inputs, workflow, required capabilities, guidance with native paths/digests, artifact/check obligations, reused contracts, source snapshots, decisions and identities for profile, request, lock and scope. `RequestPlan.check_specs()` and `.evidence()` expose the shared typed `CheckSpec` and `Evidence` contracts. Every planned check has `execution: not-run`.

```sh
govkit request plan request.json --previous request-plan.json --scope observed-scope.json --json
```

`observed-scope.json` has `schema_version: 1`, `paths`, and a partial `impacts` object. Observations add risk and scope; they cannot erase a positive risk or restore previously negative eligibility. Paths outside the normalized request make the request unbounded. Intent, policy, resources, references or scope changes produce a different identity and a reassessment signal. Repeating unchanged inputs preserves identity. A saved plan is replayed against its embedded inputs to detect edited selections; it does not authenticate those inputs.

**Planning boundary:** scope observations supplied to `request plan` are not derived from Git. Actual-change conformance compares accepted intent with real changes and trusted current policy/resources, then executes explicitly selected checks. A ready plan is neither conformance nor approval. CLI exit 0 means a plan was produced, including plans with unresolved decisions; exit 1 means invalid/unreadable inputs. Inspect blocking `decisions` or `RequestPlan.ready` for planning readiness.

Seven runnable fixtures under `governance/examples/workflows/` cover defect, enhancement, refactor, MCP, LLM, full Gherkin delivery and architecture migration. Their shared consumer is illustrative; it is not accepted policy for the GovKit source repository. Fast tests and the runtime-only wheel smoke exercise all seven, with native guidance checked for all three agents.

## Checking the actual change

Use `govkit conform --request ... --base ... --policy-target ...`.
See [CHANGE_CONFORMANCE.md](CHANGE_CONFORMANCE.md) for trusted inputs, real Git
scope, proportional artifacts, explicit tests, scoped transitions and limitations.
A request plan alone remains a proposal, not conformance or approval.
