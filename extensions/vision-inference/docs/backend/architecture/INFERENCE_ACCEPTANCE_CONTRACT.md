# Inference Acceptance Contract

**Applies to:** consumption of a pretrained or hosted vision model. Governs how a
**black-box** model — one you cannot retrain — is acceptance-tested on *your* data
before and after every change that can move its behavior.

> You cannot improve a consumed model, but you are still accountable for its
> behavior in your system. The lever you do control is a held-out acceptance set
> and a gate that re-runs when the model, provider, or preprocessing changes.

---

## 1. A frozen acceptance set

- Maintain a **held-out acceptance set** representative of production inputs, with
  ground-truth labels, kept stable so results are comparable over time.
- It is evaluated as a **black box** — inputs in, predictions out — through the same
  adapter and preprocessing production uses.
- The set's contents and version are recorded; changing it is a reviewed change.

## 2. Metrics are per-class and per-slice — never a single scalar

- Report metrics **per class** and across **slices** (lighting, resolution,
  occlusion, and — where biometric — demographic cohorts). Aggregate accuracy can
  rise while a safety-critical class or cohort collapses.
- Pin the **eval protocol** with the numbers: confidence threshold, IoU threshold,
  NMS settings, max detections. Metrics are uncomparable without it.
- Record results against the consumed `model_id` + `model_version`
  (`MODEL_VERSIONING_CONTRACT.md`) and the acceptance-set version.

## 3. Re-gate on every behavior-moving change

The acceptance gate runs — and must pass — when any of these change:

- the `model_id` / `model_version`,
- the provider or adapter,
- the boundary preprocessing,
- a detected drift in a hosted model.

A regression beyond the agreed tolerance band blocks the change.

## 4. Confidence-threshold decision policy + human-in-the-loop

- The system declares **what it does with low-confidence predictions**: a confidence
  threshold per class/use-case, and a defined **human-in-the-loop** path for
  predictions below it or in high-stakes cases.
- The decision taken (accepted / rejected / routed-to-human) is recorded in the
  prediction record so the policy is auditable.

## 5. What requires an ADR

- Shipping a model/provider/preprocessing change without passing the acceptance
  gate.
- Gating on aggregate metrics only, with no per-class/per-slice breakdown.
- Auto-accepting low-confidence predictions in a high-stakes path with no
  human-in-the-loop.

## 6. Anti-patterns

- "Accuracy is 94%" with no per-class or per-slice view.
- Comparing this week's metric to last week's without pinning the model version or
  eval protocol.
- A demographic cohort silently regressing because only the aggregate was watched.
