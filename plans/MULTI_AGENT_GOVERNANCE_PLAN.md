# Multi-Agent Governance Plan

**Status:** Pending approval  
**Scope:** All three coding agents — claude-code, copilot, codex  
**Level:** L5 only (opt-in via `multi_agent: true` in `eval_criteria.yaml`)

---

## Why This Change

The current govkit framework governs single-LLM features well: LiteLLM gateway, LangGraph node rules, DeepEval/Promptfoo evaluation. But it has no governance for *multi-agent orchestration* — the pattern where an orchestrating system prompt routes tasks to specialized agents, each with defined responsibilities, typed state contracts, and their own system prompts.

The core insight: in a multi-agent system, the **agent topology graph is the business logic** and **system prompts are the source code**. Both need governance discipline — contracts, ADRs for changes, evaluation for quality — just like code. Neither is governed today.

`docs/backend/architecture/AGENT_ARCHITECTURE.md` already exists and is the right home. It defines LangGraph usage, typed state, prompt versioning, and ADR triggers. This plan extends it with multi-agent topology governance rather than introducing a new contract file.

Multi-agent governance is **opt-in at L5**, triggered by declaring `multi_agent: true` in `eval_criteria.yaml`. Not all L5 features are multi-agent. The pattern follows the existing `mode: llm` conditional-check design.

---

## Agent Structure Reference

| Concern | claude-code | copilot | codex |
|---|---|---|---|
| Root instructions | `claude-md/l5-*.md` → `CLAUDE.md` | `copilot-instructions/l5-*.md` → `.github/copilot-instructions.md` | `agents-md/l5-*.md` → `AGENTS.md` |
| Layer rules | `rules/backend/*.md` → `.claude/rules/` | `instructions/backend/*.instructions.md` → `.github/instructions/` | `rules/backend/*.md` → nested `AGENTS.md` per layer |
| Skills | `skills/backend/*/SKILL.md` → `.claude/skills/` | `skills/backend/*/SKILL.md` → `.github/skills/` | `skills/backend/*/SKILL.md` → `.agents/skills/` |
| Skill invocation | `/skill-name` | `/skill-name` | `$skill-name` |
| Manifest | `agents/claude-code/manifest.json` | `agents/copilot/manifest.json` | `agents/codex/manifest.json` |

Skills use identical SKILL.md content across all three agents. Only the deployment path and invocation prefix differ, both managed by the manifest.

---

## New Files (9)

### Shared

**`ci/github/multi-agent-gate.yml`**  
GitHub Actions gate. Triggers when `multi_agent: true` appears in any feature's `eval_criteria.yaml`. Two jobs:
- `topology-check` — validates `agent_topology.md` exists and contains: `## Orchestrator`, `## Specialist Agents`, `## Routing Logic`, `## Failure Modes`
- `system-prompt-check` — reads `agent_topology.md`, extracts all `system_prompt:` path declarations, verifies each file exists in the repo

**`ci/azure/multi-agent-gate.yml`**  
Azure DevOps mirror of the GitHub gate. Same logic, Azure pipeline syntax (stages/jobs).

**`features/starter_backend_l5/agent_topology.md`**  
Starter template showing a concrete orchestrator + 2 specialists pattern. Shipped as part of the L5 starter so `govkit init` gives developers a real working example.

### claude-code agent

**`agents/claude-code/rules/backend/multi-agent.md`**  
Path-scoped rule. Fires on `**/agents/**`, `**/graphs/**`, `**/orchestrators/**`.

Rules:
- Graph definitions belong in `services/graphs/` — not in adapters or API layer
- State must be typed as `TypedDict` — no untyped dicts passed between nodes
- All LLM calls in graph nodes route through `LLMPort` — no direct provider SDK calls
- System prompts loaded from file at runtime — no inline strings in Python code
- No direct agent-to-agent calls — all routing goes through graph edges

Prohibited:
- Untyped state passed between nodes
- Hardcoded system prompt strings in graph node functions
- Direct imports of `openai`, `anthropic`, or other provider SDKs in graph files
- Agent-to-agent calls bypassing the LangGraph graph

**`agents/claude-code/skills/backend/multi-agent-design/SKILL.md`**  
Pre-planning skill invoked via `/multi-agent-design <feature_name>`. Must run before `/architecture-preflight` for multi-agent features. Forces the developer to answer:
- Does this feature actually require multiple agents? (justify or stop)
- What is the orchestrator's role?
- What are the specialist agents? For each: role, input state fields, output state fields, system prompt path (`src/agents/<name>/system_prompt.md`), LLM model alias
- What is the routing logic? (conditions for each graph edge)
- What is the handoff protocol? (which state fields transfer, how missing fields are handled)
- What are the failure modes? (per-node timeout, graph-level fallback)
- What cross-agent eval metrics are needed?

Output: writes `features/<feature_name>/agent_topology.md`

### copilot agent

**`agents/copilot/instructions/backend/multi-agent.instructions.md`**  
Copilot equivalent of the claude-code rule. Same content, with `applyTo: "**/agents/**, **/graphs/**, **/orchestrators/**"` frontmatter per copilot instructions convention.

**`agents/copilot/skills/backend/multi-agent-design/SKILL.md`**  
Identical SKILL.md content to the claude-code version. Deployed to `.github/skills/multi-agent-design/` via manifest. Skill invoked via `/multi-agent-design`.

### codex agent

**`agents/codex/rules/backend/multi-agent.md`**  
Same content as the claude-code rule. Deployed as a nested `AGENTS.md` in the `agents/`, `graphs/`, and `orchestrators/` directories of the target project via manifest.

**`agents/codex/skills/backend/multi-agent-design/SKILL.md`**  
Identical SKILL.md content to the claude-code version. Deployed to `.agents/skills/multi-agent-design/` via manifest. Skill invoked via `$multi-agent-design`.

---

## Modified Files (22)

### Shared

**`docs/backend/architecture/AGENT_ARCHITECTURE.md`**  
Extend the existing contract with four targeted additions:

- **New Section 17: Multi-Agent Topology** — defines `agent_topology.md` as a required governance artifact when `multi_agent: true` in `eval_criteria.yaml`; specifies required sections (Orchestrator definition with role and system prompt path; Specialist Agents each with role, input/output state fields, system prompt path, and model alias; Routing Logic with explicit edge conditions; Failure Modes with per-node timeout and graph-level fallback)

- **Extend Section 5 (Prompt Management)** — make system prompt path a mandatory field in each agent's entry in `agent_topology.md`; clarify the file convention: `src/agents/<agent_name>/system_prompt.md`; system prompts loaded at runtime, never hardcoded

- **Extend Section 10 (Evaluation Integration)** — add cross-agent eval tier: system-level evaluation measures the composed output of the full graph, not individual node outputs; reference the `multi_agent_evaluation` block in `eval_criteria.yaml`; cross-agent eval runs in CI via `multi-agent-gate.yml`

- **Extend Section 14 (ADR Requirements)** — add explicit ADR triggers for multi-agent topology changes: adding or removing graph nodes, rerouting edges, changing a node's state schema, making material changes to a system prompt

**`cli/validate.py`**  
Add 2 new check functions and register them in `_build_checks` for L5.

New constant:
```python
_AGENT_TOPOLOGY_MD = "agent_topology.md"
_RE_MULTI_AGENT = r"^multi_agent:\s*true"
```

New helper:
```python
def _is_multi_agent(feature_dir: Path) -> bool | None:
    """Returns True if multi_agent: true in eval_criteria.yaml, None if file missing."""
    eval_path = feature_dir / _EVAL_CRITERIA_YAML
    if not eval_path.exists():
        return None
    return bool(re.search(_RE_MULTI_AGENT, eval_path.read_text(encoding="utf-8"), re.MULTILINE))
```

New check 1:
```python
def check_agent_topology_exists(feature_dir: Path) -> tuple[bool, str]:
    """When multi_agent: true, agent_topology.md must exist and be non-empty."""
    if not _is_multi_agent(feature_dir):
        return True, "multi_agent not declared — agent topology check not applicable"
    path = feature_dir / _AGENT_TOPOLOGY_MD
    if not path.exists():
        return False, f"{_AGENT_TOPOLOGY_MD} missing — required when multi_agent: true"
    if path.stat().st_size == 0:
        return False, f"{_AGENT_TOPOLOGY_MD} is empty"
    return True, f"{_AGENT_TOPOLOGY_MD} present"
```

New check 2:
```python
def check_agent_topology_sections(feature_dir: Path) -> tuple[bool, str]:
    """When multi_agent: true, agent_topology.md must have all required sections."""
    if not _is_multi_agent(feature_dir):
        return True, "multi_agent not declared — agent topology sections check not applicable"
    path = feature_dir / _AGENT_TOPOLOGY_MD
    if not path.exists():
        return False, f"{_AGENT_TOPOLOGY_MD} not found"
    text = path.read_text(encoding="utf-8")
    required = [
        (r"^##\s+Orchestrator", "Orchestrator"),
        (r"^##\s+Specialist Agents", "Specialist Agents"),
        (r"^##\s+Routing Logic", "Routing Logic"),
        (r"^##\s+Failure Modes", "Failure Modes"),
    ]
    missing = [name for pattern, name in required
               if not re.search(pattern, text, re.MULTILINE)]
    if missing:
        return False, f"{_AGENT_TOPOLOGY_MD} missing sections: {', '.join(missing)}"
    return True, f"{_AGENT_TOPOLOGY_MD} has all required sections"
```

In `_build_checks`, add both functions to the L5 check list after `check_l5_preflight_sections`.

**`tests/test_validate.py`**  
Add `TestMultiAgentValidation` class:
- `check_agent_topology_exists`: multi_agent true + file missing → fail; file present → pass; not declared → skip (True); empty file → fail
- `check_agent_topology_sections`: all sections present → pass; one missing → fail with section name; not declared → skip; file missing → fail
- Integration: L5 `_build_checks` includes both new checks in the correct position

**`governance/schemas/evaluation_prediction.schema.json`**  
Add optional `multi_agent_evaluation` object inside `evaluation_prediction`:
```json
"multi_agent_evaluation": {
  "type": "object",
  "properties": {
    "topology_validated":            { "type": "boolean" },
    "system_prompt_governed":        { "type": "boolean" },
    "cross_agent_coherence":         { "$ref": "#/definitions/score_entry" },
    "orchestrator_routing_accuracy": { "$ref": "#/definitions/score_entry" }
  },
  "required": ["topology_validated", "system_prompt_governed"]
}
```

**`features/starter_backend_l5/eval_criteria.yaml`**  
Add commented-out `multi_agent` block showing the flag and cross-agent eval dimensions. Developers uncomment when building a multi-agent feature:
```yaml
# Uncomment when building a multi-agent feature:
# multi_agent: true
# multi_agent_evaluation:
#   topology_validated: false
#   system_prompt_governed: false
#   cross_agent_coherence:
#     score: null
#     evidence: ""
#   orchestrator_routing_accuracy:
#     score: null
#     evidence: ""
```

**`governance/backend/templates/l5-plan.md`**  
Add a **Multi-Agent Configuration** section (conditional, appears when `multi_agent: true`):
- Agent topology reference: `features/<feature>/agent_topology.md`
- State schema path: `services/graphs/<feature>_state.py`
- System prompt paths per agent (table: agent name → file path)
- Cross-agent eval prediction block using `multi_agent_evaluation` schema fields

**`governance/backend/templates/l5-architecture-preflight.md`**  
Add **Section 15: Agent Topology** at the end. Only required when `multi_agent: true`. Template text:
- Is `agent_topology.md` present and complete?
- Does each agent have a typed state contract?
- Does each system prompt file exist at its declared path?
- Is an ADR required for this topology? (Yes if this is a new multi-agent feature or topology change)
- Section 15 status: Approved / Blocked

---

### claude-code agent

**`agents/claude-code/skills/backend/architecture-preflight/SKILL.md`**  
Add **Section 15: Agent Topology Check** at the end of the preflight checklist:
```
## 15. Agent Topology (multi-agent features only)

Check if `features/$ARGUMENTS/eval_criteria.yaml` declares `multi_agent: true`.

If yes:
- [ ] `agent_topology.md` exists — HALT and request `/multi-agent-design $ARGUMENTS` if missing
- [ ] Orchestrator role and system prompt path are declared
- [ ] Each specialist agent has: role, typed input/output state, system prompt path, model alias
- [ ] Routing logic covers all edge conditions
- [ ] Failure modes specify per-node timeout and graph-level fallback
- [ ] ADR status confirmed for this topology

Section 15 status: Approved / Blocked
```

**`agents/claude-code/skills/backend/genai-preflight/SKILL.md`**  
Add **Section 6: Multi-Agent Validation** (runs only when `multi_agent: true`):
- Confirm each agent's system prompt file exists at the declared path in `agent_topology.md`
- Confirm graph state schema is a `TypedDict` in `services/graphs/`
- Confirm `eval_criteria.yaml` includes `multi_agent_evaluation` block with `topology_validated` and `system_prompt_governed`
- Confirm LangGraph is approved in `docs/backend/architecture/TECH_STACK.md`
- Block if any item fails; update Section 15 of `architecture_preflight.md`

**`agents/claude-code/claude-md/l5-backend-api.md`**  
Add three targeted additions:
1. Under architecture contracts: "If `eval_criteria.yaml` declares `multi_agent: true`, read `docs/backend/architecture/AGENT_ARCHITECTURE.md` Section 17 before planning."
2. Under ADR rules: "Agent topology changes (adding/removing/rerouting nodes, material system prompt changes, state schema changes) require an ADR."
3. Under feature lifecycle: "For multi-agent features: run `/multi-agent-design` before `/architecture-preflight`."

**`agents/claude-code/claude-md/l5-backend-cli.md`**  
Same three additions as `l5-backend-api.md`.

**`agents/claude-code/manifest.json`**  
In both `type.api.level_5` and `type.cli.level_5` overrides:
- Add to `files`: `{ "src": "rules/backend/multi-agent.md", "dest": ".claude/rules/multi-agent.md" }`
- Add to `files`: `{ "src": "skills/backend/multi-agent-design/", "dest": ".claude/skills/multi-agent-design/" }`
- Add to `ci.github.level_5.shared`: `"ci/github/multi-agent-gate.yml"`
- Add to `ci.azure.level_5.shared`: `"ci/azure/multi-agent-gate.yml"`

---

### copilot agent

**`agents/copilot/skills/backend/architecture-preflight/SKILL.md`**  
Same Section 15 addition as claude-code version.

**`agents/copilot/skills/backend/genai-preflight/SKILL.md`**  
Same Section 6 addition as claude-code version.

**`agents/copilot/copilot-instructions/l5-backend-api.md`**  
Same three additions as claude-code `l5-backend-api.md`.

**`agents/copilot/copilot-instructions/l5-backend-cli.md`**  
Same three additions as claude-code `l5-backend-cli.md`.

**`agents/copilot/manifest.json`**  
In both `type.api.level_5` and `type.cli.level_5` overrides:
- Add to `files`: `{ "src": "instructions/backend/multi-agent.instructions.md", "dest": ".github/instructions/multi-agent.instructions.md" }`
- Add to `files`: `{ "src": "skills/backend/multi-agent-design/", "dest": ".github/skills/multi-agent-design/" }`
- Add to `ci.github.level_5.shared`: `"ci/github/multi-agent-gate.yml"`
- Add to `ci.azure.level_5.shared`: `"ci/azure/multi-agent-gate.yml"`

---

### codex agent

**`agents/codex/skills/backend/architecture-preflight/SKILL.md`**  
Same Section 15 addition as claude-code version. Skill invocation style uses `$architecture-preflight`.

**`agents/codex/skills/backend/genai-preflight/SKILL.md`**  
Same Section 6 addition as claude-code version. Skill invocation style uses `$genai-preflight`.

**`agents/codex/agents-md/l5-backend-api.md`**  
Same three additions as claude-code `l5-backend-api.md`. Skill references use `$multi-agent-design`.

**`agents/codex/agents-md/l5-backend-cli.md`**  
Same three additions as claude-code `l5-backend-cli.md`. Skill references use `$multi-agent-design`.

**`agents/codex/manifest.json`**  
In both `type.api.level_5` and `type.cli.level_5` overrides:
- Add to `files`: `{ "src": "rules/backend/multi-agent.md", "dest": "agents/AGENTS.md" }` (or per codex nested AGENTS.md convention — confirm path pattern from existing L5 rules)
- Add to `files`: `{ "src": "skills/backend/multi-agent-design/", "dest": ".agents/skills/multi-agent-design/" }`
- Add to `ci.github.level_5.shared`: `"ci/github/multi-agent-gate.yml"`
- Add to `ci.azure.level_5.shared`: `"ci/azure/multi-agent-gate.yml"`

---

## Implementation Sequence

These must be done in order:

1. Extend `AGENT_ARCHITECTURE.md` — establishes the contract everything else references
2. `agent_topology.md` starter template — concrete working example of Section 17
3. Rule/instruction files for all 3 agents — code-level enforcement
4. `multi-agent-design` SKILL.md for all 3 agents — the skill that produces `agent_topology.md`
5. Architecture preflight + genai preflight updates for all 3 agents — checks topology exists and is valid
6. Root instruction updates for all 3 agents — wires the skill into the L5 lifecycle
7. `validate.py` + tests — runtime enforcement via `govkit validate`
8. `manifest.json` updates for all 3 agents — deploys rule and skill via `govkit apply`
9. CI gates — enforces topology and system prompt checks in pipeline
10. Schema + template updates — evaluation prediction schema and plan/preflight templates

---

## File Count Summary

| Category | New | Modified |
|---|---|---|
| Shared (docs, CI, validation, templates) | 3 | 7 |
| claude-code agent | 2 | 5 |
| copilot agent | 2 | 5 |
| codex agent | 2 | 5 |
| **Total** | **9** | **22** |

**31 files total.**

---

## Verification

After implementation:

1. `pytest tests/test_validate.py -v` — all existing tests pass; new `TestMultiAgentValidation` tests pass
2. Create a test feature with `multi_agent: true` in `eval_criteria.yaml`, no `agent_topology.md` → `govkit validate --level 5` exits 1 with clear error
3. Same feature with `agent_topology.md` missing sections → exits 1, names the missing sections
4. Same feature with a complete `agent_topology.md` → exits 0
5. `govkit apply --agent claude-code --level 5 --target <tmpdir>` → verify `.claude/rules/multi-agent.md` and `.claude/skills/multi-agent-design/SKILL.md` are present
6. `govkit apply --agent copilot --level 5 --target <tmpdir>` → verify `.github/instructions/multi-agent.instructions.md` and `.github/skills/multi-agent-design/SKILL.md` are present
7. `govkit apply --agent codex --level 5 --target <tmpdir>` → verify codex-equivalent paths contain the new rule and skill
8. Inspect all three manifests to confirm new L5 entries reference valid source paths
9. Review `AGENT_ARCHITECTURE.md` Section 17 and extended sections 5, 10, 14 for clarity and completeness
