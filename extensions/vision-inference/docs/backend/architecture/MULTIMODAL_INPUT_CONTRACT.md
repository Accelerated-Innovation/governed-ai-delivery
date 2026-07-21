# Multimodal Input Contract

**Applies to:** consumption of a **generative / vision-language model** (a VLM such
as Claude vision or GPT-4V, or image generation / diffusion). This is the net-new,
vision-specific contract for generative consumption — everything else reuses the L5
GenAI-Ops contracts (see "Relationship to L5" below).

> A generative vision model takes **image + text** and produces **content**. That
> doubles the attack and quality surface versus a discriminative model: the image is
> now an *instruction channel*, and the output is generated content that must be
> guarded and evaluated — not a bounded label set.

---

## 1. The image is an untrusted instruction channel

- Treat image inputs to a VLM as **untrusted instructions**, not just data.
  **Prompt-injection-via-image** (text embedded in the image, adversarial overlays,
  steganographic instructions) can override the system prompt.
- The system prompt and developer instructions are isolated from user-supplied
  image/text content; user content can never be promoted to system authority.
- Image provenance/size/format expectations are validated at the boundary before the
  call (consistent with `VISION_MODEL_ADAPTER_CONTRACT.md` preprocessing).

## 2. Validate generated output before use

- Generated text/images are **validated before** they are surfaced or acted on —
  never trusted verbatim. Structured outputs are schema-checked; free-form outputs
  pass the guardrail checks in §4.
- Generated **images** are themselves subject to the safety checks below (a VLM/
  diffusion model can produce unsafe or infringing content).

## 3. Multimodal inputs carry the biometric obligations

- An image sent to a hosted VLM is still potentially biometric/personal data —
  `BIOMETRIC_DATA_HANDLING_CONTRACT.md` applies in full (consent, residency,
  retention, minimize, never log raw payload). Sending a face to a VLM is sending it
  to a third party exactly as with a discriminative API.

## 4. Relationship to L5 (reuse, don't reinvent)

This contract **extends**, and does not duplicate, the core L5 GenAI-Ops contracts
(declared in the manifest's `relates_to.extends`):

- `extensions/llm-application/docs/backend/architecture/MODEL_GUARDRAILS_CONTRACT.md` — input/output safety (NSFW, unsafe, infringing content)
  applies to image+text prompts and to generated images/text.
- `extensions/llm-application/docs/backend/architecture/LLM_EVALUATION_CONTRACT.md` — eval-as-judge for open-ended VLM output replaces the
  bounded per-class acceptance metrics used for discriminative models.
- `extensions/llm-application/docs/backend/architecture/LLM_OBSERVABILITY_CONTRACT.md` — generation logging/tracing (PII-safe; never the
  raw image).
- `extensions/llm-application/docs/backend/architecture/LLM_GATEWAY_CONTRACT.md` — hosted VLM calls route through the governed gateway.

If a project does not have the L5 contracts installed, this contract set's
`relates_to.extends` paths will be missing and `govkit doctor` / `validate` will flag
them — the generative layer is meant for L5-governed projects.

## 5. What requires an ADR

- Passing user-supplied image/text into a position that can override system
  instructions.
- Surfacing or acting on generated output with no validation/guardrail pass.
- Sending images to a VLM without satisfying `BIOMETRIC_DATA_HANDLING_CONTRACT.md`.

## 6. Anti-patterns

- Concatenating a user's caption request into the system prompt.
- Rendering a model-generated image to end users without a safety check.
- Treating "it's just an image" as exempt from biometric handling because the model
  is generative.
