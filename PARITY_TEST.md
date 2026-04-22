# Parity Test Guide — Language-Agnostic Agent Refactoring

## Objective

Verify that the refactored agent rules (which reference `docs/` instead of embedding language specifics) produce **identical guidance and code output** for Python/FastAPI projects as the original embedded-content version.

**Key constraint:** All `docs/backend/architecture/` files remain unchanged and continue to contain FastAPI/Python content. The refactored agents read these docs and produce the same behavior as before.

---

## Refactoring Summary

**Changed:** 36 files across 3 agents (Claude Code, GitHub Copilot, OpenAI Codex)
- 12 rules files (`agents/*/rules/backend/*.md`, `agents/*/rules/cli/*.md`)
- 12 main entry files (`agents/*/claude-md/`, `copilot-instructions/`, `agents-md/`)
- 12 L3 entry files (spec-driven, no eval)
- 12 L5 entry files (GenAI operations, with eval)

**Pattern:** Every rule now starts with:
```markdown
**Your project's <layer> conventions:** `docs/backend/architecture/<DOC>.md`

Read this document before implementing. It defines your project's <details>.

**Universal constraints (apply to any language):**
- [architecture principle 1]
- [architecture principle 2]
```

**Unchanged:** All documentation files (`docs/backend/architecture/`, `docs/backend/evaluation/`, `governance/`, features/, etc.)

---

## Parity Test Scope

Parity testing focuses on **guidance parity** — verifying that agents read docs and produce consistent output patterns. Full code generation validation is out of scope (requires interactive IDE testing).

### What is Tested

1. **Doc reference correctness** — rules correctly point to relevant docs
2. **Constraint consistency** — universal constraints match original rules intent
3. **Feature lifecycle** — preflight → planning → implementation flow unchanged
4. **Evaluation framework** — FIRST and 7 Virtue thresholds unchanged
5. **Architecture enforcement** — boundary checks, ADR triggers, port/adapter patterns unchanged

### What is NOT Tested (out of scope)

- Full code generation for a complete feature (requires Claude Code IDE)
- Integration with GitHub Copilot chat
- Integration with OpenAI Codex API
- Runtime behavior of generated code

---

## Checklist: Verify Refactoring Completeness

Run these checks to confirm all files were updated:

```bash
cd /path/to/governed-ai-delivery

# Claude Code rules: should find 6 files
grep -l "Your project" agents/claude-code/rules/backend/*.md agents/claude-code/rules/cli/*.md | wc -l
# Expected: 6

# Claude Code main entries: should find 6 files with Project Documentation
grep -l "Project Documentation" agents/claude-code/claude-md/backend-api.md agents/claude-code/claude-md/backend-cli.md \
  agents/claude-code/claude-md/l3-backend-api.md agents/claude-code/claude-md/l3-backend-cli.md \
  agents/claude-code/claude-md/l5-backend-api.md agents/claude-code/claude-md/l5-backend-cli.md | wc -l
# Expected: 6

# GitHub Copilot rules: should find 6 files
grep -l "Your project" agents/copilot/instructions/backend/*.md agents/copilot/instructions/cli/*.md | wc -l
# Expected: 6

# GitHub Copilot main entries: should find 6 files
grep -l "Project Documentation" agents/copilot/copilot-instructions/backend-api.md \
  agents/copilot/copilot-instructions/backend-cli.md \
  agents/copilot/copilot-instructions/l3-backend-api.md \
  agents/copilot/copilot-instructions/l3-backend-cli.md \
  agents/copilot/copilot-instructions/l5-backend-api.md \
  agents/copilot/copilot-instructions/l5-backend-cli.md | wc -l
# Expected: 6

# OpenAI Codex rules: should find 6 files
grep -l "Your project" agents/codex/rules/backend/*.md agents/codex/rules/cli/*.md | wc -l
# Expected: 6

# OpenAI Codex main entries: should find 6 files
grep -l "Project Documentation" agents/codex/agents-md/backend-api.md \
  agents/codex/agents-md/backend-cli.md \
  agents/codex/agents-md/l3-backend-api.md \
  agents/codex/agents-md/l3-backend-cli.md \
  agents/codex/agents-md/l5-backend-api.md \
  agents/codex/agents-md/l5-backend-cli.md | wc -l
# Expected: 6

# Total: 36 files should be refactored
```

**✓ All checks pass:** Refactoring is complete.

---

## Parity Test Steps (Manual IDE Testing)

### Setup: Create a minimal Python/FastAPI feature

Use `features/schema_contract_example/` as a reference (complete feature with acceptance criteria, NFRs, plan, eval criteria, preflight).

Or create a new minimal feature:

```bash
mkdir -p features/parity_test_api
touch features/parity_test_api/{acceptance.feature,nfrs.md,eval_criteria.yaml,plan.md,architecture_preflight.md}
```

Fill these with basic content:
- `acceptance.feature`: One Gherkin scenario (e.g., "User can login")
- `nfrs.md`: Basic NFRs (performance, security)
- `plan.md`: One increment with tests and deliverables
- `eval_criteria.yaml`: FIRST and 7 Virtue criteria
- `architecture_preflight.md`: Basic preflight (ports, adapters, no ADR required)

### Step 1: Verify Agent Initialization

**Claude Code (IDE):**
1. Open Claude Code in your IDE
2. Open a file in `features/parity_test_api/`
3. Verify Claude reads:
   - The feature artifacts (acceptance.feature, nfrs.md, plan.md)
   - The agent rules from `.claude/rules/backend/api.md` or `cli.md`
   - **Expected:** Claude references `docs/backend/architecture/API_CONVENTIONS.md` (or relevant doc) in guidance

**GitHub Copilot (IDE):**
1. Open GitHub Copilot chat
2. Ask: `@github-copilot-instructions How should I structure the API routes for parity_test_api?`
3. **Expected:** Copilot references `docs/backend/architecture/API_CONVENTIONS.md` and provides FastAPI-style guidance

**OpenAI Codex (API):**
1. Send a prompt to Codex with the feature artifacts
2. Include the instructions from `agents/codex/agents-md/backend-api.md`
3. **Expected:** Codex responses reference `docs/backend/architecture/` and use FastAPI patterns

### Step 2: Run Architecture Preflight (Claude Code only)

In Claude Code:
```
/architecture-preflight parity_test_api
```

**Expected output (same as original version):**
- Layer analysis: API → Services → Ports → Adapters
- Boundary violations: none
- ADR triggers: none (for simple feature)
- Port/adapter contracts: defined

### Step 3: Run Spec Planning (Claude Code only)

```
/spec-planning parity_test_api
```

**Expected output:**
- Feature increments defined
- Test approach: pytest + FastAPI TestClient
- Evaluation compliance summary with FIRST and 7 Virtue predictions
- References to `docs/backend/architecture/API_CONVENTIONS.md`, `TESTING.md`, `TECH_STACK.md`

### Step 4: Compare Guidance Patterns

**Test:** Agent guidance should include these FastAPI patterns (sourced from `docs/`):

- ✓ Routes use versioned paths: `/v1/<resource>`
- ✓ Request models inherit from `BaseModel`
- ✓ Responses wrapped in `ApiResponse` envelope
- ✓ Auth uses `Depends(get_current_user)`
- ✓ Port delegation in route handlers
- ✓ Exception mapping to HTTP status codes
- ✓ Tests use `TestClient` from `fastapi.testclient`

**Why this works:** The docs haven't changed — they still contain FastAPI specifics. Refactored agents read these docs and produce identical patterns.

### Step 5: Implement One Increment (Claude Code)

Generate code for the first increment of `parity_test_api`:

1. Click in `parity_test_api/api/routes.py` (or create it)
2. Ask Claude Code: `Implement the first increment of parity_test_api`
3. Verify generated code:
   - Routes are FastAPI endpoints
   - Routes call ports (delegate to domain)
   - Request models are Pydantic `BaseModel`
   - Responses use standard envelope

**Compare to original version:** Code structure should match the patterns from the original FastAPI-embedded rules (now sourced from docs).

### Step 6: Run Tests

```bash
cd features/parity_test_api
pytest tests/ -v
```

**Expected:** Tests pass (same test framework, patterns, and assertions as original version).

---

## Validation Success Criteria

✓ **Refactoring completeness:** All 36 files updated (verified by grep checks above)

✓ **Doc reference correctness:** Every rules file references the appropriate `docs/backend/architecture/` file

✓ **Guidance consistency:** Agents produce guidance that mentions `docs/` files, not embedded language specifics

✓ **FastAPI pattern recognition:** For Python projects, agents still guide toward:
  - Pydantic models
  - FastAPI decorators
  - Dependency injection (`Depends`)
  - TestClient
  - Status code mapping

✓ **Evaluation thresholds:** FIRST and 7 Virtue thresholds unchanged (verified in `$spec-planning` output)

✓ **Test approach:** Same testing framework (pytest, TestClient, mock approaches)

✓ **Architecture enforcement:** Same boundary checks, port/adapter patterns, ADR triggers

---

## Failure Modes & Troubleshooting

### Issue: Agent does not reference `docs/backend/architecture/` files

**Cause:** Rules file not updated with doc reference
**Fix:** Check that the rules file in `.claude/rules/` or `copilot/instructions/` contains the line:
```markdown
**Your project's <layer> conventions:** `docs/backend/architecture/<DOC>.md`
```

### Issue: Agent provides language-specific guidance (e.g., "Use Click for CLI") that contradicts FastAPI docs

**Cause:** Doc reference syntax is incorrect or agent skipped the rules
**Fix:** 
1. Verify the rules file exists and is correctly scoped (paths: or applyTo:)
2. Verify the agent initialization reads from the correct rules directory

### Issue: Generated code uses old patterns (embedded in rules) instead of doc-referenced patterns

**Cause:** Agent is reading cached rules; regeneration needed
**Fix:** Clear agent cache and restart IDE

### Issue: Python project guidance includes non-FastAPI patterns (e.g., Django, Go)

**Cause:** `docs/backend/architecture/` files were modified to a different stack
**Fix:** Verify docs still contain FastAPI content; revert if necessary
```bash
git diff docs/backend/architecture/API_CONVENTIONS.md
git diff docs/backend/architecture/TECH_STACK.md
```

---

## Parity Test Results Template

After running the tests, document results:

```markdown
## Parity Test Results

**Date:** [date]
**Tested Agent:** Claude Code | GitHub Copilot | OpenAI Codex
**Python Project:** features/parity_test_api (or other)
**Docs Stack:** FastAPI (unchanged from original)

### Refactoring Completeness
- [ ] All 6 rules files updated
- [ ] All 6 main entry files updated
- [ ] Project Documentation section present and correct

### Guidance Parity
- [ ] Agent references `docs/backend/architecture/` files
- [ ] FastAPI patterns are still recommended
- [ ] FIRST and 7 Virtue evaluation approach unchanged
- [ ] Architecture preflight output matches original version

### Code Output Parity
- [ ] Generated routes use FastAPI decorators
- [ ] Request models use Pydantic BaseModel
- [ ] Authentication uses Depends(get_current_user)
- [ ] Port delegation present in route handlers
- [ ] Test approach uses pytest + TestClient

### Architecture Enforcement
- [ ] Boundary checks enforced (no circular deps)
- [ ] Port/adapter patterns recognized
- [ ] ADR triggers correctly identified
- [ ] Shared artifact contracts respected

### Tests
- [ ] Unit tests pass (FIRST compliant)
- [ ] Integration tests pass (Gherkin-mapped)
- [ ] Evaluation gates pass (FIRST and 7 Virtue thresholds)

### Conclusion
**PASS** | **FAIL** — [summary]
```

---

## Next Steps

After parity testing confirms the refactoring:

1. **Document language customization process** — how teams using C#, Go, Java can customize `docs/` for their stack
2. **Create C# example docs** — template `docs/backend/architecture/API_CONVENTIONS.md` for ASP.NET Core projects
3. **Add language selection to govkit CLI** — `govkit apply --language csharp --framework aspnetcore`
4. **Create per-language parity test suites** — validate agents work for Python, C#, Go, Java

---

## References

- **Refactored rules:** `agents/claude-code/rules/`, `agents/copilot/instructions/`, `agents/codex/rules/`
- **Main entry points:** `agents/claude-code/claude-md/`, `agents/copilot/copilot-instructions/`, `agents/codex/agents-md/`
- **Docs (unchanged):** `docs/backend/architecture/API_CONVENTIONS.md`, `CLI_CONVENTIONS.md`, `ARCH_CONTRACT.md`, etc.
- **Evaluation:** `docs/backend/evaluation/eval_criteria.md`
- **Plan:** See `IMPROVEMENT_PLAN.md` for context and timeline
