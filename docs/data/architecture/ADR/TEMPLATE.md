# ADR-XXX: <Short Decision Title>

## Status
Proposed | Accepted | Rejected | Superseded

## Date
YYYY-MM-DD

## Authors
- <Name / Role>

---

## 1. Context

Describe:

- The model, pipeline, or data product impacted
- Relevant architectural constraints (layering, freshness, materialization)
- Existing standards or contracts that apply
- The problem this decision addresses

Reference:
- `features/<feature_name>/plan.md`
- Relevant sections of `ARCH_CONTRACT.md`
- Relevant boundary rules in `BOUNDARIES.md`
- Source freshness / SLA expectations in `PIPELINE_CONTRACT.md`

---

## 2. Decision

State the decision clearly and concisely.

Avoid narrative here. This section must stand alone.

Example:

> We will materialize `dim_customers` as `incremental` (merge strategy) rather
> than `table`, because the daily full rebuild exceeds the warehouse cost
> budget defined in `PIPELINE_CONTRACT.md`.

---

## 3. Architectural Impact

### 3.1 Layer Boundaries
- Layers affected (staging / intermediate / marts):
- New models introduced and their layer:
- Cross-source joins introduced (must live in intermediate):

Confirm:
- No staging model joins across sources
- No mart reads another mart in a way that violates `BOUNDARIES.md`
- Dependency direction (staging → intermediate → marts) is preserved

### 3.2 Data Contract Impact
If applicable:
- Mart column additions / removals / renames:
- Grain changes (does the primary key change?):
- Downstream consumers affected (BI, reverse-ETL, other teams):
- Breaking-change coordination required per `BOUNDARIES.md`:
- Materialization change (view / table / incremental / ephemeral):

### 3.3 PII / Compliance Impact
- New PII columns introduced:
- Masking strategy (`mask_pii()` macro per `PII_HANDLING_CONTRACT.md`):
- New PII category beyond the default set:
- Column-lineage capture required per `LINEAGE_CONTRACT.md`:
- Environment exposure (is raw PII reachable in dev/ci?) per `ENVIRONMENTS.md`:

---

## 4. Alternatives Considered

For each alternative:

### Option A
- Description
- Pros
- Cons
- Why rejected

Keep this section concise but explicit.

---

## 5. Evaluation Impact

Does this decision affect:

- LLM evaluation criteria?
- Deterministic evaluation checks (schema tests, freshness checks)?
- CI enforcement rules?

If yes:
- List affected criteria from `features/<feature_name>/eval_criteria.yaml`
- Describe changes required

If no:
- State: "No evaluation impact."

---

## 6. Risks and Tradeoffs

- Data quality risks (late-arriving data, nulls, duplicates):
- Freshness / SLA risks:
- Cost implications (warehouse compute, storage):
- Backfill / reprocessing implications:

Mitigations:

---

## 7. Plan Alignment

Reference:

- Feature plan increments impacted:
- New increment required?
- Scope adjustments required?

If the decision changes scope:
- `plan.md` must be updated.

---

## 8. Consequences

### Positive
- 

### Negative
- 

### Neutral
- 

---

## 9. Follow-Up Actions

- Model changes required:
- Test changes required (schema / singular / freshness):
- Documentation updates required (exposures, model descriptions):
- CI updates required:
- Data governance / privacy review required:

---

## 10. Approval

Approved by:
- Data architect / lead:
- Privacy / compliance (if PII impact):
- Product / downstream owner (if contract impact):
