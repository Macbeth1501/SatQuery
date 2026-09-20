# SatQuery AI — System & Product Design Document (SPDD)
### SIH26167 — Ground-Truth Engineering Reference

**Status:** Baseline v1.0 — build-ready

> **Implementation note (2026-09-20):** this document is the design baseline and is deliberately not rewritten to track the build. Where the prototype differs from it (PDF via `xhtml2pdf` rather than `weasyprint`; SQLite via stdlib `sqlite3` rather than Postgres; no containers or CI yet; deterministic dummy specialists in place of models), the adopted resolution is recorded in `SatQuery_AI_Development_Plan.md` Appendix B, and current status is in `PROGRESS_LOG.md`.
**Scope of this document:** This SPDD operationalizes the *Final Synthesized Solution* (see companion document `SatQuery_AI_Final_Synthesized_Solution.md`) into a concrete, buildable system: component specs, data contracts, APIs, storage, training pipelines, deployment topology, NFRs, error handling, testing strategy, and repo layout. Where the proposal document argued *why*, this document specifies *what to build, exactly*. Any implementation decision not covered here should be resolved by consulting §17 (Open Questions) and updating this document — this is meant to be the single source of truth the team builds against, not a pitch artifact.

---

## Table of Contents

1. Purpose, Scope & Conventions
2. Requirements Traceability Matrix
3. High-Level Architecture
4. Component Design — Orchestration Layer
5. Component Design — Specialist Layer
6. Component Design — Fusion Pipeline
7. Component Design — Verifier & Confidence
8. Data Contracts & Schemas
9. API Specification
10. Storage & Persistence Design
11. Model Training Pipeline Design
12. Frontend / UI Design
13. Non-Functional Requirements
14. Error Taxonomy & Failure Handling
15. Deployment Architecture
16. Testing & Evaluation Strategy
17. Open Questions, Assumptions & Risks Carried Forward
18. Repository Structure
19. Glossary
20. Appendix — Sequence Walkthroughs

---

## 1. Purpose, Scope & Conventions

### 1.1 Purpose
This document is the engineering ground truth for building SatQuery AI. Every module described here maps to a specific line item in the SIH26167 problem statement's evaluation rubric (see §2). Anyone joining the build should be able to read this document and know: what service to write, what it accepts, what it returns, what it must validate, and what "done" looks like for that piece.

### 1.2 In-scope vs. out-of-scope for this SPDD
- **In scope:** everything listed as "Buildable with high confidence" and "Realistic stretch goals" in the proposal's Feasibility Assessment.
- **Out of scope (explicitly, per the proposal's §9):** full MLOps hardening (Triton/TensorRT export, drift monitors, CI/CD adapter-regression gating), Kubernetes autoscaling, a QGIS plugin, a vector database for historical recall, and an end-to-end generative optical-SAR fusion model trained from scratch. These are named in §17 as deferred, not forgotten.

### 1.3 Conventions used in this document
- Service names are written in `snake_case` and match the directory names in §18.
- JSON Schema fragments use `camelCase` field names for API-facing contracts and `snake_case` for internal Python objects, matching typical FastAPI/Pydantic conventions.
- Every component section follows the same sub-structure: **Responsibility → Inputs → Outputs → Internal Logic → Failure Modes → Interfaces to Other Components.**
- "MUST" / "SHOULD" / "MAY" are used in the RFC 2119 sense throughout.

---

## 2. Requirements Traceability Matrix

Every PS evaluation-rubric row is mapped to the specific component(s) responsible for it. This table MUST be kept in sync as the design evolves — it is the acceptance criteria for "does the system satisfy the PS," independent of demo polish.

| PS Evaluation Area | Responsible Component(s) | Section |
|---|---|---|
| Single-Image VQA | `vqa_caption_specialist` | §5.1 |
| Image Captioning / Scene Description | `vqa_caption_specialist` | §5.1 |
| Region Grounding | `grounding_specialist` | §5.2 |
| Multitemporal Change Analysis | `change_vqa_specialist` | §5.3 |
| Change-Based VQA | `change_vqa_specialist` | §5.3 |
| Optical-SAR Analysis | `fusion_pipeline` | §6 |
| Remote-Sensing Adaptation | Training pipeline for all specialists | §11 |
| Agentic Orchestration | `query_interpreter`, `compatibility_validator`, `specialist_router` | §4 |
| Input Validation | `compatibility_validator` | §4.2 |
| Evidence & Visual Output | `verifier_node`, `response_composer`, evidence overlay renderer | §7, §12 |
| Execution Trace | `trace_emitter` | §7.3 |
| Overall System Performance | End-to-end integration, NFRs | §13, §16 |
| Downloadable Reports | `report_service` | §9.6, §12.4 |

---

## 3. High-Level Architecture

### 3.1 Service decomposition

SatQuery AI is decomposed into the following logical services. In the hackathon deployment topology (§15) several of these are co-located in one process/container to reduce operational overhead; the boundaries below are *logical*, not necessarily *physical*, deployment units.

```
┌───────────────────────────────────────────────────────────────────────┐
│  web_frontend  (React)                                                 │
└───────────────────────────┬─────────────────────────────────────────┘
                             │ HTTPS / multipart + JSON (REST)
┌───────────────────────────▼─────────────────────────────────────────┐
│  api_gateway  (FastAPI)                                                │
│    - auth (optional, session-token based for hackathon)               │
│    - request validation (HTTP-layer schema only)                      │
│    - routes to orchestrator_service                                   │
└───────────────────────────┬─────────────────────────────────────────┘
                             │
┌───────────────────────────▼─────────────────────────────────────────┐
│  orchestrator_service                                                  │
│    ┌─────────────────┐   ┌──────────────────────┐                    │
│    │ query_interpreter │→ │ compatibility_validator │→ (reject w/reason)│
│    └─────────────────┘   └──────────┬───────────┘                    │
│                                     ▼                                  │
│                          ┌────────────────────┐                       │
│                          │ specialist_router   │                       │
│                          └─────┬──────┬──────┬─┘                       │
│         ┌────────────────────┘      │      └─────────────────┐        │
│         ▼                           ▼                        ▼        │
│  vqa_caption_specialist   change_vqa_specialist      fusion_pipeline   │
│  grounding_specialist                                                  │
│         └────────────────────┬──────┴────────────────────────┘        │
│                               ▼                                        │
│                        verifier_node                                   │
│                               ▼                                        │
│                     confidence_scorer + trace_emitter                  │
│                               ▼                                        │
│                        response_composer                               │
└───────────────────────────┬─────────────────────────────────────────┘
                             │
┌───────────────────────────▼─────────────────────────────────────────┐
│  model_serving  (vLLM / HF transformers process, shared backbone +     │
│                  hot-swappable LoRA adapters)                          │
└─────────────────────────────────────────────────────────────────────┘

┌────────────────────┐   ┌───────────────────┐   ┌───────────────────┐
│  object_store       │   │  metadata_db (SQL) │   │  report_service    │
│  (images, overlays,  │   │  (sessions, traces,│   │  (PDF/JSON export) │
│   adapter weights)   │   │   evidence ledgers)│   │                    │
└────────────────────┘   └───────────────────┘   └───────────────────┘
```

### 3.2 Request lifecycle (one sentence per stage)

1. Frontend uploads image(s) + query → `api_gateway`.
2. `api_gateway` creates a `session_id`, stores raw images in `object_store`, forwards a `AnalyzeRequest` to `orchestrator_service`.
3. `query_interpreter` produces a `TaskSpec`.
4. `compatibility_validator` checks the `TaskSpec` against image metadata and specialist preconditions; on failure, returns a `ValidationRejection` and the pipeline stops.
5. `specialist_router` dispatches to one or more specialists per the `TaskSpec.taskType` (see §4.3 routing table).
6. Each specialist calls `model_serving` with its adapter ID and returns an `EvidenceItem`.
7. `verifier_node` runs geometric + cross-tool checks over the collected `EvidenceLedger`.
8. `confidence_scorer` computes a tiered confidence badge.
9. `trace_emitter` serializes the full `ExecutionTrace`.
10. `response_composer` produces the final `AnalyzeResponse` (answer text + evidence + confidence + trace + report link).
11. `api_gateway` persists the trace/ledger to `metadata_db`, returns the response to the frontend.
12. On request, `report_service` renders the persisted trace + evidence into a downloadable PDF/JSON.

---

## 4. Component Design — Orchestration Layer

### 4.1 `query_interpreter`

**Responsibility:** Convert a free-text natural-language query (plus image-count/modality context) into a structured `TaskSpec`.

**Inputs:**
- `query: str` — raw user text.
- `imageContext: ImageContextSummary` — output of metadata extraction (§4.2), includes count, per-image modality guess, format.

**Outputs:** `TaskSpec` (schema in §8.1).

**Internal logic:**
- Implemented as a small, text-only instruct LLM (no vision) called in structured function-calling / JSON-mode, constrained to emit only fields defined in the `TaskSpec` JSON Schema.
- Few-shot exemplars are drawn verbatim from the PS's own "Representative Queries" section (5 examples) plus 10–15 additional hand-written exemplars covering ambiguous phrasing, to bias the model toward the PS's exact task taxonomy rather than a generic open-ended classification.
- `taskType` MUST be one of the fixed enum in §8.1 — the interpreter is never permitted to emit a free-text task name (this is what makes the "hallucinated tool" failure mode structurally impossible, per the design rationale in the proposal §4.2).
- If the model's own emitted `intentConfidence` (self-reported, on a 0–1 scale, requested explicitly in the prompt) is below `0.55`, the interpreter MUST set `TaskSpec.status = "ambiguous"` and MUST populate `TaskSpec.clarifyingQuestion` instead of guessing. This is a deliberate low bar for triggering a clarifying question, since a wrong guess is more costly than one extra round-trip.

**Failure modes:**
- LLM emits invalid JSON → retry once with a "your last output was invalid JSON, here is the schema again" repair prompt; on second failure, return a hard `interpretation_failed` error (§14) rather than guessing.
- LLM emits a `taskType` not in the enum → treated identically to invalid JSON (schema validation catches this before it reaches downstream components).

**Interfaces:** Called synchronously by `orchestrator_service`; calls `model_serving`'s text-only endpoint (does not touch the vision backbone).

---

### 4.2 `compatibility_validator`

**Responsibility:** Decide, before any specialist runs, whether the `TaskSpec` is physically satisfiable given the uploaded image(s). This is the component responsible for the PS's "Input Validation" rubric row and MUST be able to *reject* a request with a specific, human-readable reason.

**Inputs:**
- `TaskSpec` (from §4.1).
- `ImageMetadata[]` — per image: format, CRS (if present), band count/order, detected modality (optical/multispectral/SAR), resolution/GSD, footprint polygon, acquisition timestamp (if present in tags), nodata percentage.

**Outputs:** either
- `ValidationPass { taskSpec, normalizedInputs }`, or
- `ValidationRejection { reasonCode, humanReadableReason, missingRequirement }`.

**Internal logic — precondition table (this is the core "GeoGraphRAG-style structural precondition" mechanism referenced in the proposal §5.4):**

Each specialist in the registry declares a static, machine-readable precondition block. The validator evaluates these deterministically — **no LLM is involved in this step**, by design, since this is exactly the class of check that must be reproducible and auditable.

| Specialist | Required image count | Required modality | Required temporal relationship | Required spatial relationship | Format constraints |
|---|---|---|---|---|---|
| `vqa_caption_specialist` | 1 | optical, multispectral, or SAR | n/a | n/a | GeoTIFF/TIFF/PNG/JPEG |
| `grounding_specialist` | 1 | optical or multispectral | n/a | n/a | GeoTIFF/TIFF/PNG/JPEG |
| `change_vqa_specialist` | 2 | same modality on both images | acquisition dates MUST differ | footprint overlap ≥ 70% (configurable threshold) | GeoTIFF/TIFF/PNG/JPEG |
| `fusion_pipeline` | 2 | one optical/multispectral + one SAR | same-time preferred; MUST NOT be flagged bi-temporal unless user explicitly requests combined change+fusion (routed as a 2-step plan, §4.3) | footprint overlap ≥ 70%, same/compatible CRS or reprojectable | GeoTIFF/TIFF (PNG/JPEG only for benchmark datasets, per PS) |

**Validation steps, in order (all MUST run; short-circuit on first hard failure):**
1. Format sniff via GDAL — reject unsupported formats immediately.
2. Modality detection — band count/order and, where available, sensor metadata tags used to classify optical vs. multispectral vs. SAR; ambiguous cases fall back to a lightweight heuristic classifier (not a full specialist model) trained on BigEarthNet.txt's own modality labels.
3. Count check against the specialist(s) selected by `TaskSpec.taskType`.
4. For pairs: CRS compatibility check (reproject if resolvable via `pyproj`, else reject with `crs_mismatch_unresolvable`), footprint overlap via `shapely` IoU, and — for change tasks — acquisition-date ordering.
5. Radiometric sanity: nodata/cloud-mask percentage below a configurable threshold (default 40%); above threshold, do not hard-reject but attach a `warnings[]` entry that flows through to the final confidence score as a soft discount.
6. On any hard failure, populate `ValidationRejection` with a `reasonCode` from the fixed enum in §14.1 and a specific, templated human-readable string (never a raw exception message).

**Failure modes:** see §14.1 (Validation error taxonomy).

**Interfaces:** Called by `orchestrator_service` immediately after `query_interpreter`; reads from `object_store` (image bytes/headers) via a metadata-extraction helper; writes nothing itself — validation results are passed in-memory to `specialist_router` or returned directly to the caller on rejection.

---

### 4.3 `specialist_router`

**Responsibility:** Deterministic, non-LLM mapping from a validated `TaskSpec` to one or more specialist calls, including sequencing for compound queries.

**Routing table (fixed, testable, MUST NOT be modified by any runtime LLM decision):**

| `TaskSpec.taskType` | Specialist(s) invoked | Sequencing |
|---|---|---|
| `single_vqa` | `vqa_caption_specialist` | single call |
| `single_caption` | `vqa_caption_specialist` | single call |
| `single_grounding` | `grounding_specialist` | single call |
| `change_vqa` | `change_vqa_specialist` | single call |
| `change_description` | `change_vqa_specialist` | single call |
| `change_and_grounding` (PS example: "what changed and where") | `change_vqa_specialist` → `grounding_specialist` (grounding runs over the change-difference map region) | sequential, 2 calls |
| `fusion` | `fusion_pipeline` | single call (internally 3 sub-steps, §6) |
| `fusion_then_change` (PS example: "use optical+SAR to find X, then say if X increased") | `fusion_pipeline` → `change_vqa_specialist` | sequential, 2 calls |

**Internal logic:** a pure lookup (`dict`/`match` statement in implementation) from `taskType` (+ a boolean `requiresSequencing` flag set by `query_interpreter` when it detects a compound query pattern) to an ordered list of specialist call specs. This table is unit-testable in isolation (§16.2) without invoking any model.

**Failure modes:** `taskType` not present in the table is impossible by construction, since `query_interpreter`'s output schema enum is a subset of this table's keys — this invariant MUST be enforced by a schema/table consistency test in CI.

**Interfaces:** consumes `ValidationPass`, produces an ordered `List[SpecialistCallSpec]` consumed by the specialist-invocation loop in `orchestrator_service`.

---

## 5. Component Design — Specialist Layer

All specialists share one frozen visual encoder + one frozen LLM decoder, served once by `model_serving`; a specialist call is, mechanically, "run inference with LoRA adapter X and task-token Y." This section specifies each specialist's *task contract*, not its training recipe (training is §11).

### 5.1 `vqa_caption_specialist`

- **Adapter:** `adapter_vqa_caption` (jointly trained, §11.2).
- **Input contract:** 1 image (any supported modality) + a `mode` field (`"vqa"` or `"caption"`) + for `vqa`, the free-text question.
- **Output contract:** `{ answerText: str, answerType: "open_ended"|"binary"|"mcq", boundingBoxesIfAny: [], rawTokenConfidence: float }`.
- **Task token:** `[vqa]` or `[caption]` prepended per the shared task-conditioning convention (§11.5).
- **Notes:** for closed-set style questions matching RSVQA's known question types, the specialist MUST constrain decoding to the valid answer vocabulary (yes/no, land-cover class names) when the interpreter has tagged the question as closed-set; otherwise decode open-ended.

### 5.2 `grounding_specialist`

- **Adapter:** `adapter_grounding` (separately trained, §11.2 — this is the deliberate deviation from a single joint adapter, justified in the proposal §5.1).
- **Input contract:** 1 image (optical/multispectral only) + a referring expression (e.g., "the water body").
- **Output contract:** `{ boxes: [{xLeft, yTop, xRight, yBottom, theta, normalizedTo100: true}], isAmbiguous: bool, candidateCount: int }`.
- **Behavior on ambiguity:** if more than one plausible region matches the referring expression (detected via multiple above-threshold candidate boxes), the specialist MUST return **all** plausible boxes with per-box scores rather than silently picking the top-1 — this is a hard requirement, not a stretch behavior, because it is the demo-critical differentiator called out in the proposal §4.2.

### 5.3 `change_vqa_specialist`

- **Adapter:** `adapter_change_vqa` (separately trained on CDVQA, §11.3).
- **Input contract:** 2 co-registered same-modality images (T1, T2) + question (for change-VQA) or no question (for change-description, uses a default prompt).
- **Output contract:** `{ answerText: str, changeMaskAvailable: bool, changeMaskRef: str|null, quantityFlag: bool, deterministicPixelCount: int|null }`.
- **Internal deterministic cross-check (mandatory, not optional):** whenever `TaskSpec` or the interpreter has tagged the question as quantity/ratio-type (e.g., "how much," "increased/decreased," "smallest change"), the specialist MUST also compute a deterministic pixel/instance count from its internal change-attention map (if a mask is produced) and populate `deterministicPixelCount` and set `quantityFlag = true`. This value is consumed downstream by `verifier_node` (§7.1) to cross-check the LLM's stated answer — the specialist does not resolve the discrepancy itself, it only surfaces the two numbers.

### 5.4 Adapter hot-swap contract (applies to §5.1–5.3)

`model_serving` MUST expose a single inference endpoint parameterized by `adapterId` and `taskToken`; it MUST NOT require reloading the full backbone per specialist call. Implementation detail: LoRA deltas are kept resident in memory for all adapters simultaneously (they are small — target <50MB per adapter at rank 8–16 on a 1–4B backbone), and only the active delta is merged/applied per forward pass. This is a hard NFR (§13.2) because sequential compound queries (§4.3) call two specialists per request and cannot tolerate a full model reload between them.

---

## 6. Component Design — Fusion Pipeline

**Responsibility:** Implement the structured, two-stage optical-SAR fusion approach specified in the proposal (§5.3), as a single logical specialist with three internal sub-steps.

**Input contract:** 1 optical/multispectral image + 1 co-registered SAR image (validated by `compatibility_validator`, §4.2) + the user's query.

**Sub-step 1 — Independent single-image evidence extraction.**
Calls `vqa_caption_specialist` internally, once per modality, requesting structured (not free-text) output: LULC class presence list with per-class confidence, approximate area share, and any grounded regions relevant to the query. Implementation note: this reuses the exact same adapter and endpoint as §5.1 — the fusion pipeline is a *composition* of the single-image specialist, not a separately trained model for this sub-step, exactly as scoped for hackathon feasibility.

**Sub-step 2 — Complementarity detector.**
- **Input:** the two structured evidence sets from sub-step 1.
- **Output:** per-LULC-region tags: `"agreement" | "optical_only" | "sar_only"`, each with a numeric agreement score.
- **Model:** a small classifier trained on BigEarthNet.txt's paired S1/S2 labels using an InfoNCE contrastive alignment objective between SAR-DINO and RGB-DINO dense features (MM-OVSeg's validated CMU recipe), NOT a hand-written rule table — this is the specific upgrade over a purely rule-based detector called out in the proposal §5.3. Served as its own lightweight endpoint in `model_serving` (a dense-feature encoder pair, not the LLM decoder).
- **Fallback:** if the contrastive-trained detector is not ready in time (stretch-goal risk, per proposal §9), a rule-based fallback (class-presence-set intersection/difference between the two modalities' structured evidence) MUST be wired in behind the same interface, so the rest of the pipeline is unaffected by which implementation is active. This fallback switch is a config flag, not a code branch scattered through the pipeline.

**Sub-step 3 — Verbalization.**
The controller LLM (same decoder used by `response_composer`) is given the tagged, structured comparison and produces natural-language text that explicitly cites which modality supplied which claim (e.g., "SAR imagery reveals a water body in the north-east quadrant not visible in the optical scene, consistent with cloud cover there"). This step MUST NOT be given raw pixels — only the structured, already-tagged evidence — to keep the fusion pipeline's actual mechanism auditable and distinct from an opaque end-to-end model.

**Output contract:** `{ answerText: str, regionTags: [{region, tag, score}], opticalEvidenceRef: str, sarEvidenceRef: str }`.

**Domain-gap mitigation hook:** before sub-step 1, both images pass through the GSD-normalization/radiometric-jitter preprocessing stage (§11.4) — this is a pipeline-level preprocessing concern, not something either sub-step implements itself, so it applies uniformly to every specialist, not just fusion.

---

## 7. Component Design — Verifier & Confidence

### 7.1 `verifier_node`

**Responsibility:** Cross-check the collected `EvidenceLedger` before anything is shown to the user. Three check classes, all MUST run (not configurable off):

1. **Geometric sanity (deterministic, no ML):**
   - Every returned bounding box MUST lie within `[0,100]` normalized image bounds.
   - A change mask's spatial extent MUST NOT exceed the co-registered overlap region computed during validation (§4.2).
   - Oriented box angles MUST fall within `[-90°, 90°]`.
   - Violations set `EvidenceItem.geometryValid = false` and are logged verbatim into the trace.

2. **Cross-tool agreement (for multi-specialist / multi-sample plans):**
   - When the same underlying question is answerable from two independent evidence sources in the ledger (e.g., fusion's `regionTags` vs. a direct VQA call on the same region), compare them; disagreement above a configurable threshold sets `EvidenceLedger.agreementFlag = "low"`.

3. **Deterministic quantity cross-check (change-VQA specific, mandatory when `quantityFlag = true` from §5.3):**
   - Compare `change_vqa_specialist`'s `answerText`-derived numeric claim (extracted via a small regex/NLI parse of the answer) against `deterministicPixelCount`. If they diverge beyond a tolerance band (default ±15%), set `EvidenceItem.quantityDiscrepancy = true`.

**Output:** an annotated `EvidenceLedger` (same object, with `geometryValid`, `agreementFlag`, `quantityDiscrepancy` fields populated) — the verifier does not rewrite the answer text; it only annotates evidence for the confidence scorer to consume.

### 7.2 `confidence_scorer`

**Responsibility:** Produce a three-tier badge (`High` / `Medium` / `Low`) plus a short rationale string, never a raw numeric probability (per the proposal's explicit rejection of false-precision scoring, §5.5).

**Algorithm, in priority order (first applicable rule wins — this is intentionally a simple, auditable decision list, not a learned scorer, for hackathon-timeframe reliability):**

1. If `verifier_node` set `geometryValid = false` on any evidence item consumed by the final answer → **Low**, rationale = "a geometric consistency check failed."
2. Else if `quantityDiscrepancy = true` → **Low**, rationale = "the model's stated count/ratio disagrees with a deterministic pixel-based count."
3. Else if the query type matches the literature-documented weak-point list (counting, ratio, smallest-change, non-unique-referent grounding) → apply a fixed one-tier discount to whatever tier steps 4–5 would otherwise produce (e.g., would-be High becomes Medium).
4. Else if the decoupled perception/reasoning confidence tokens (§7.2.1, stretch goal) are both available and both above their respective calibration thresholds → **High**.
5. Else → **Medium** (the default when nothing above triggers a downgrade and the stretch-goal decoupled-token signal is unavailable — this is the MVP-path default described in the proposal's feasibility tiering).

**§7.2.1 Decoupled perception/reasoning confidence (stretch goal):** if implemented, the specialist is prompted to emit two separate confidence tokens — one for "did I correctly perceive the relevant visual evidence" and one for "did I correctly reason from that evidence to the answer" — calibrated against a held-out validation slice (not the test split) using a simple isotonic/Platt-scaling fit. If not implemented in time, the MVP falls back to rules 1–3 and 5 only, per the proposal's explicit fallback plan.

### 7.3 `trace_emitter`

**Responsibility:** Serialize the complete `ExecutionTrace` object (schema §8.4) — this is a first-class structured output field on every response, not a debug log, because the PS explicitly states only the observable trace is evaluated.

**Contents (all MUST be present on every response, even rejections):** selected `taskType`, every specialist/tool invoked with its adapter ID and version string, all permitted parameters actually used, per-step wall-clock timing, the final confidence tier and rationale, and — for a `ValidationRejection` — the `reasonCode` and human-readable explanation in place of a normal trace body.

---

## 8. Data Contracts & Schemas

All schemas below are the authoritative contracts. Implementation MUST use these as the Pydantic models / JSON Schemas; do not invent parallel ad hoc dict shapes.

### 8.1 `TaskSpec`

```json
{
  "taskType": "single_vqa | single_caption | single_grounding | change_vqa | change_description | change_and_grounding | fusion | fusion_then_change",
  "status": "resolved | ambiguous",
  "targetObject": "string | null",
  "questionText": "string | null",
  "requiredImageCount": "integer",
  "requiredModalities": ["optical|multispectral|sar", "..."],
  "requiresTemporalPairing": "boolean",
  "requestedParameters": { "iouThreshold": "float?", "topK": "integer?" },
  "intentConfidence": "float (0-1)",
  "clarifyingQuestion": "string | null"
}
```

### 8.2 `ImageMetadata`

```json
{
  "imageId": "string",
  "format": "geotiff | tiff | png | jpeg",
  "crs": "string | null",
  "bandCount": "integer",
  "detectedModality": "optical | multispectral | sar",
  "gsdMeters": "float | null",
  "footprintPolygon": "geojson geometry | null",
  "acquisitionTimestamp": "iso8601 | null",
  "nodataPercent": "float",
  "cloudMaskPercent": "float | null"
}
```

### 8.3 `EvidenceLedger` / `EvidenceItem`

```json
{
  "sessionId": "string",
  "items": [
    {
      "sourceSpecialist": "string",
      "adapterId": "string",
      "answerText": "string | null",
      "boxes": [ { "xLeft": 0, "yTop": 0, "xRight": 0, "yBottom": 0, "theta": 0 } ],
      "maskRef": "string | null",
      "regionTags": [ { "region": "string", "tag": "agreement|optical_only|sar_only", "score": 0.0 } ],
      "deterministicPixelCount": "integer | null",
      "quantityFlag": "boolean",
      "geometryValid": "boolean",
      "quantityDiscrepancy": "boolean"
    }
  ],
  "agreementFlag": "high | low | n/a"
}
```

### 8.4 `ExecutionTrace`

```json
{
  "sessionId": "string",
  "selectedTaskType": "string",
  "steps": [
    {
      "stepIndex": 0,
      "component": "string",
      "adapterIdOrVersion": "string | null",
      "parametersUsed": {},
      "wallClockMs": 0,
      "outputSummary": "string"
    }
  ],
  "confidenceTier": "High | Medium | Low",
  "confidenceRationale": "string",
  "rejection": { "reasonCode": "string", "humanReadableReason": "string" } 
}
```

### 8.5 `AnalyzeRequest` / `AnalyzeResponse` (API-facing, see §9)

```json
// AnalyzeRequest (multipart: images[] + JSON body below)
{
  "query": "string",
  "sessionOptions": { "returnReport": "boolean" }
}

// AnalyzeResponse
{
  "sessionId": "string",
  "answerText": "string | null",
  "evidence": { "boxes": [], "masks": [], "overlayImageUrls": [] },
  "confidence": { "tier": "High|Medium|Low", "rationale": "string" },
  "executionTrace": { "...": "see 8.4" },
  "reportUrl": "string | null",
  "rejected": "boolean",
  "rejectionReason": "string | null"
}
```

---

## 9. API Specification

Base path: `/v1`. All endpoints return `application/json` except where noted.

### 9.1 `POST /v1/analyze`
- **Body:** multipart form — `images[]` (1–2 files) + `query` (string) + optional `sessionOptions` (JSON string field).
- **Response:** `AnalyzeResponse` (§8.5). `200` on success or graceful rejection (rejections are NOT a 4xx — a validated-but-unsatisfiable query is a normal, expected outcome and is returned as `rejected: true` with a `200`, per the design goal of the Compatibility Validator being a first-class, non-exceptional part of the flow). Malformed requests (missing query, unsupported file type Content-Type) DO return `400`.
- **Latency target:** see §13.1.

### 9.2 `GET /v1/session/{sessionId}`
- Returns the persisted `AnalyzeResponse` for a prior session (for re-opening a trace panel or re-downloading a report without recomputing).

### 9.3 `GET /v1/session/{sessionId}/report`
- **Query params:** `format=pdf|json`.
- Streams the rendered report file. `404` if the session doesn't exist; `409` if the session's original request was rejected (nothing to report).

### 9.4 `GET /v1/health`
- Liveness/readiness probe; checks `model_serving` reachability and `metadata_db` connectivity. Returns `200` / `503`.

### 9.5 `GET /v1/registry`
- Returns the current specialist registry (adapter IDs, versions, and their precondition blocks from §4.2) — used by the frontend to render capability hints and by integration tests to assert the router/validator tables are in sync.

### 9.6 `report_service` (internal, not directly HTTP-exposed beyond §9.3)
- Consumes a persisted `ExecutionTrace` + `EvidenceLedger` + original images, renders a PDF via `weasyprint` (HTML template → PDF) and a parallel raw JSON export. The PDF template MUST include: query text, answer, confidence badge + rationale, evidence images with overlays, and the full step-by-step execution trace table — i.e., it is a direct rendering of already-computed data, not a component that computes anything new.

---

## 10. Storage & Persistence Design

### 10.1 `object_store`
- Local filesystem (hackathon) or S3-compatible bucket (if available), organized as:
  - `/{sessionId}/inputs/{imageId}.{ext}` — original uploads, immutable.
  - `/{sessionId}/derived/{imageId}_normalized.tif` — post domain-gap-normalization tiles.
  - `/{sessionId}/evidence/{stepIndex}_overlay.png` — rendered evidence overlays (boxes/masks drawn on the image).
  - `/{sessionId}/report.pdf`, `/{sessionId}/report.json`.
- Images are content-addressed by a hash of their bytes for the caching optimization described in §13.3 (repeat queries on the same image reuse the cached vision-encoder embedding rather than re-encoding).

### 10.2 `metadata_db`
A single relational schema (SQLite for local dev / Postgres for a shared demo deployment) with three tables:

- **`sessions`**: `session_id (pk), created_at, query_text, task_type, rejected (bool), confidence_tier`.
- **`evidence_ledgers`**: `session_id (fk), ledger_json (jsonb)` — the full `EvidenceLedger` stored as JSON rather than normalized, since it is read/written wholesale, never queried field-by-field at this project's scale.
- **`execution_traces`**: `session_id (fk), trace_json (jsonb)`.

This intentionally minimal schema (JSON-blob storage keyed by session) is a deliberate simplicity choice for the hackathon timeframe — a fully normalized schema is unnecessary engineering effort for a system whose query pattern is "fetch everything for one session ID."

### 10.3 Model artifact storage
- Frozen backbone weights: stored once, loaded by `model_serving` at startup.
- LoRA adapter deltas (`adapter_vqa_caption`, `adapter_grounding`, `adapter_change_vqa`): versioned directories `{adapterId}/{version}/adapter_model.safetensors`, all loaded resident in memory per §5.4.
- Complementarity-detector weights (§6, sub-step 2): stored alongside adapters, loaded by a separate lightweight endpoint in `model_serving`.

---

## 11. Model Training Pipeline Design

### 11.1 Shared preprocessing (applies to all training runs)
1. Ingest BigEarthNet.txt via `reBEN`'s `rico-hdl` conversion into an LMDB/safetensors store for high-throughput random-batch reads.
2. Apply the ScoreRS-style quality-scoring filter (§11.1.1) before any fine-tuning run — this MUST run once, upstream of all three adapters, producing a single filtered training pool they each subsample from.
3. Respect the official geographic (not naive grid) train/val/test split to avoid the leakage BigEarthNet's original split is documented to suffer from.

**§11.1.1 Quality-scoring filter:** a small learned scorer (trainable on a manually-labeled sample of ~1–2K pairs, or, if time doesn't allow training one, a heuristic proxy — caption length + LULC-label count + no-data percentage threshold) ranks training pairs; the bottom quartile is dropped before fine-tuning. This step MUST be logged (pairs in, pairs kept) so its effect is auditable in the technical write-up.

### 11.2 `adapter_vqa_caption` (joint) and `adapter_grounding` (separate)
- **Backbone:** frozen ViT/CLIP-style visual encoder (CLIP-ViT-L/14) + frozen 1–4B instruct LLM decoder.
- **Trainable:** modality-specific linear projection layers (S1/S2 token bridges) + LoRA (rank 8–16, target modules: attention Q/K/V/O projections) on the LLM only.
- **`adapter_vqa_caption` data:** BigEarthNet.txt's captioning + binary/MCQ VQA annotations, filtered per §11.1.1.
- **`adapter_grounding` data:** BigEarthNet.txt's referring-expression annotations, same filter, trained separately per the task-interference rationale in the proposal §5.1.
- **Loss:** autoregressive cross-entropy over the answer/caption token sequence; for grounding, cross-entropy over the tokenized bounding-box string `{xLeft,yTop,xRight,yBottom|theta}` (box regression re-cast as sequence generation — keeps the output head identical in kind to the other specialists, avoiding a separate detection head).
- **Eval:** VRSBench (captioning/grounding/VQA, held out, never trained on), RSVQA (closed-set VQA cross-check).

### 11.3 `adapter_change_vqa`
- **Data:** CDVQA (from SECOND), official train/val/test1/test2 split; test2 (the harder, distribution-shifted split) is retained as the honest reporting split, not cherry-picked test1.
- **Architecture addition:** a Change-Enhancing Module — Siamese-encoded T1/T2 features combined via a difference-attention mechanism, not naive subtraction.
- **Loss:** cross-entropy over the answer sequence, with the CEM optimized jointly end-to-end (no separate auxiliary loss term).
- **Eval:** CDVQA's own per-question-type accuracy + Average/Overall Accuracy, reported split by question category to expose the known counting/ratio weak point rather than averaging it away.

### 11.4 Domain-gap mitigation training data
- Applied as an **augmentation policy**, not a new model: histogram matching toward Cartosat-2S's panchromatic/multispectral response curve, speckle-noise injection matching RISAT's characteristics, GSD downsampling/upsampling — applied to a held-out slice of training data, used purely for a robustness stress-test ablation, never mixed into headline-accuracy training data.
- Optional secondary source for the complementarity-detector's alignment training (§6, sub-step 2): SOMA-1M, whose multi-resolution framing better matches the Sentinel-vs-Cartosat/RISAT gap than MM-OVSeg's CMU-Data alone.

### 11.5 Task conditioning
- Every specialist call prepends an explicit task token (`[vqa]`, `[caption]`, `[ground]`, `[change]`, `[fusion]`) to the instruction, in addition to selecting the corresponding LoRA adapter — two redundant, cross-checkable signals of task identity that `verifier_node` can use to detect an adapter/prompt mismatch.

### 11.6 Training compute budget (planning figure, not a hard SLA)
~1–2 GPU-days per adapter on a single modern multi-GPU node, for a filtered subset (not the full 464K-pair corpus) sized to fit the hackathon prep window — this is a planning assumption to be revisited against actual available compute; see §17.

---

## 12. Frontend / UI Design

### 12.1 Page structure
1. **Upload & Query page** — drag-and-drop for 1–2 images, format/size validation client-side (mirrors, does not replace, server-side validation), a text query box, and a "capability hint" panel populated from `GET /v1/registry` (§9.5) so users can see what's supported before submitting.
2. **Results page** — the `AnalyzeResponse` rendered as:
   - Answer text panel.
   - Map/image viewer with evidence overlays (boxes/masks) toggle-able per evidence item.
   - Confidence badge (colored High/Medium/Low chip + rationale tooltip).
   - Collapsible **Execution Trace panel** — rendered directly from `ExecutionTrace.steps`, expanded by default during demos per the proposal's presentation strategy.
   - "Download Report" button → `GET /v1/session/{id}/report`.
3. **Rejection state** — when `AnalyzeResponse.rejected = true`, the Results page renders a distinct, clearly-styled rejection card (not an error toast) showing `rejectionReason` verbatim — this state MUST be a first-class, polished UI state, not an afterthought, since it is the demo's differentiating moment (proposal §4.2).

### 12.2 Evidence overlay rendering
- Bounding boxes and masks are drawn client-side over the original raster using the normalized `[0,100]` coordinates from `EvidenceItem.boxes`, scaled to the displayed image's actual pixel dimensions.
- Multi-candidate grounding results (§5.2 ambiguity behavior) render **all** candidate boxes simultaneously with distinguishable styling (e.g., opacity by score) rather than only the top-1.

### 12.3 Map integration
- A lightweight Leaflet (or deck.gl) layer is used only when a valid CRS/footprint is present; for benchmark-format (PNG/JPEG) inputs without georeferencing, the viewer falls back to a plain image-overlay mode without a map basemap.

### 12.4 Report content parity
- The downloadable PDF (§9.6) MUST reproduce every element visible on the Results page (answer, confidence, evidence images, full trace table) — no information is exclusive to either the live UI or the report.

---

## 13. Non-Functional Requirements

### 13.1 Latency budgets (P95, single-tile inputs)

| Task | Target |
|---|---|
| Single-image VQA / Captioning | < 3 s |
| Grounding | < 4 s |
| Change-VQA (2 images) | < 6 s |
| Fusion (2 images, 3 internal sub-steps) | < 8 s |
| Compound (2-specialist sequential plan) | sum of the two component budgets + 0.5 s routing overhead |

P99 target: +50% over P95, with a hard timeout returning a "still processing, partial evidence available" partial response rather than an unbounded hang (frontend MUST handle this partial-response state distinctly from both success and rejection).

### 13.2 Throughput / concurrency
- Hackathon deployment target: sustain at least 3 concurrent in-flight `/v1/analyze` requests without adapter-swap contention, given the shared-backbone design (§5.4). This is a soft target for the live-demo period, not a production SLA.

### 13.3 Caching
- Vision-encoder embeddings for a given uploaded image are cached (keyed on the content hash from §10.1) so a follow-up query on the same image does not re-run validation or re-encode the image from scratch.

### 13.4 Security / governance (hackathon-scoped)
- No default network path sends uploaded imagery to a third-party hosted API — `model_serving` runs the full vision pipeline self-hosted. A clearly-labeled, opt-in fallback path MAY route the **text-only** `query_interpreter` step through a hosted LLM API for the public-benchmark demo specifically, but this MUST NOT be the default and MUST NEVER apply to any component that touches image bytes.
- Uploaded images and derived artifacts are session-scoped and MUST be deletable on request (a `DELETE /v1/session/{id}` endpoint, deferred to stretch scope but the schema in §10.2 already supports it via cascade delete on `session_id`).

### 13.5 Accessibility / offline-capability
- The full stack (frontend + orchestrator + model serving + storage) MUST be runnable via a single `docker compose up` with no required external network calls at runtime (model weights and datasets are fetched at build/setup time, not at request time).

---

## 14. Error Taxonomy & Failure Handling

### 14.1 Validation rejection reason codes (`compatibility_validator`)

| `reasonCode` | Meaning | Example human-readable text |
|---|---|---|
| `unsupported_format` | File format not in the supported set | "This file format isn't supported. Please upload GeoTIFF, TIFF, PNG, or JPEG." |
| `modality_mismatch` | Task requires a modality not present (e.g., change-VQA requested but only one optical + one SAR image supplied) | "Change analysis needs two images of the same sensor type acquired at different times — you've supplied one optical and one SAR image, which is a fusion pair, not a change pair." |
| `insufficient_image_count` | Fewer images than the task requires | "This query needs two images (before/after or optical+SAR); only one was supplied." |
| `crs_mismatch_unresolvable` | CRS mismatch that reprojection cannot resolve | "The two images use incompatible coordinate systems that could not be automatically reconciled." |
| `insufficient_footprint_overlap` | Spatial overlap below threshold | "These two images cover different geographic areas (overlap below the minimum required for a paired analysis)." |
| `temporal_ordering_invalid` | Same-date images supplied for a change task | "Change analysis requires two images from different dates; both supplied images share the same acquisition date." |
| `ambiguous_intent` | `query_interpreter` confidence below threshold | (returns `TaskSpec.clarifyingQuestion` instead of a rejection — see §4.1) |

### 14.2 Runtime failure handling (post-validation)

- **Specialist model inference error (OOM, timeout, malformed output):** caught at the `orchestrator_service` level; the affected step is marked failed in the `ExecutionTrace`, and if it was part of a sequential compound plan (§4.3), the pipeline attempts to return partial results from completed steps with confidence forced to `Low` and a rationale noting the incomplete pipeline — never a raw 500 with no explanation.
- **`model_serving` unreachable:** `api_gateway`'s `/v1/health` reflects this; `/v1/analyze` fails fast with a `503` and a retryable-error flag, rather than hanging until the latency timeout.
- **Verifier detects a geometry violation:** does not block the response; forces confidence to `Low` and includes the specific violation in the trace (per §7.1) — the system still answers, transparently flagged, rather than refusing outright, since a geometry violation is evidence of low reliability, not proof of an unanswerable query.

---

## 15. Deployment Architecture

### 15.1 Container topology (`docker-compose.yml` services)

| Service | Contains | Notes |
|---|---|---|
| `frontend` | React app (static build served via nginx or Vite preview) | Talks only to `api_gateway`. |
| `api_gateway` | FastAPI app: `api_gateway` + `orchestrator_service` co-located in one process for the hackathon topology | Splitting these into separate containers is a documented future step, not required for the demo. |
| `model_serving` | vLLM or HF `transformers` process hosting the shared backbone + all LoRA adapters + the complementarity-detector endpoint | GPU-attached container; the only service requiring a GPU. |
| `metadata_db` | Postgres (or bind-mounted SQLite file for the simplest local dev path) | |
| `object_store` | Local bind-mounted volume (or MinIO if S3-compatible semantics are wanted) | |
| `report_service` | Co-located inside `api_gateway` process (invoked as a function call, not a separate network hop) for the hackathon topology | |

### 15.2 Environment configuration
- All service URLs, adapter version pins, confidence thresholds (§7.2), and validation thresholds (§4.2, footprint overlap %, nodata %) MUST be externalized to a single `config.yaml` / `.env` pair, not hard-coded — this is what makes the precondition table (§4.2) and routing table (§4.3) testable and tunable without redeploying code.

### 15.3 Startup sequence
1. `model_serving` loads the frozen backbone once, then loads all three LoRA adapters + complementarity detector into memory.
2. `api_gateway` waits on `model_serving`'s health check before accepting traffic.
3. `metadata_db` schema migration runs (idempotent) before `api_gateway` starts.

---

## 16. Testing & Evaluation Strategy

### 16.1 Unit tests
- `compatibility_validator`: one test per row of the precondition table (§4.2) plus one per rejection reason code (§14.1) — asserting both the pass and the fail path for each.
- `specialist_router`: table-driven tests asserting every `taskType` enum value routes to the expected specialist sequence, plus a CI-enforced consistency check that the router table's key set exactly matches `TaskSpec.taskType`'s schema enum (catching drift between §4.1's schema and §4.3's table).
- `verifier_node`: synthetic `EvidenceLedger` fixtures for each of the three check classes (geometry, cross-tool agreement, quantity discrepancy), asserting correct flag-setting.
- `confidence_scorer`: table-driven tests covering the full priority-ordered rule list in §7.2, including the interaction between a weak-point-query discount and an otherwise-High base tier.

### 16.2 Integration tests
- End-to-end `/v1/analyze` calls against a small fixture set of real (or synthetically paired) images covering: a clean single-image VQA pass, a deliberately malformed pair (triggers each rejection code at least once), an ambiguous-referent grounding case (asserts multi-box return), a quantity-type change-VQA case with an injected discrepancy (asserts `Low` confidence), and one compound (`fusion_then_change`) request (asserts correct sequential specialist invocation and trace step count).

### 16.3 Model evaluation harness (offline, not part of the request-time system)
- Each adapter is evaluated on its held-out benchmark per §11.2–11.3 (VRSBench/RSVQA for VQA/caption/grounding, CDVQA test1+test2 for change) using the metrics named in those sections, run as a scheduled offline script, with results logged (not just eyeballed) so the technical write-up's reported numbers are reproducible from a committed script, not a one-off notebook run.
- The fine-tuning delta ablation (un-adapted backbone vs. LoRA-adapted) is run and recorded as part of this harness — this is the single most judge-legible proof that the mandatory adaptation requirement is genuinely met, per the proposal's demo strategy, and MUST be reproducible on demand, not just demonstrated live from memory.

### 16.4 Manual / demo-readiness checklist (run before any live demo)
- [ ] A deliberately malformed query triggers a rejection with the correct reason code and readable text.
- [ ] An ambiguous grounding query returns multiple boxes, not a silent top-1.
- [ ] A quantity-type change-VQA query with an intentionally-provoked discrepancy shows a `Low` confidence badge with the correct rationale.
- [ ] The compound `fusion_then_change` query completes within its combined latency budget and shows both specialist steps in the trace panel.
- [ ] The downloadable report matches the on-screen Results page exactly.
- [ ] The system runs fully via `docker compose up` with no runtime external network dependency.

---

## 17. Open Questions, Assumptions & Risks Carried Forward

These MUST be resolved (or explicitly re-affirmed as accepted risk) before final submission; each is carried forward from the proposal document, made concrete here.

1. **Actual available GPU compute for the fine-tuning campaign is not yet confirmed.** §11.6's "1–2 GPU-days per adapter" is a planning assumption; if compute is more constrained, the fallback (per the proposal) is a smaller stratified BigEarthNet.txt subset, and this MUST be logged transparently in the execution/report output, not silently substituted.
2. **The complementarity detector's contrastive-alignment training (§6, sub-step 2) is the single highest-risk deliverable** in this SPDD — if it is not ready in time, the rule-based fallback (already specified with a config-flag switch, §6) MUST be used and clearly labeled as such in the demo and write-up, not presented as the trained version.
3. **Decoupled perception/reasoning confidence tokens (§7.2.1) are a stretch goal**; the MVP confidence path (§7.2, rules 1–3 and 5) MUST work standalone and MUST be the tested, demo-ready path regardless of whether the stretch goal lands.
4. **Domain-shift stress-test sample sourcing (Cartosat-2S/RISAT-*like* public proxies) is not yet confirmed as accessible** — if no suitable public proxy data can be sourced in time, this becomes a documented limitation in the write-up rather than a silently-dropped feature.
5. **Auth/session model is intentionally minimal** (session-token only, no user accounts) for the hackathon scope — full RBAC (as sketched in Parth's original draft) is explicitly deferred, consistent with the proposal's out-of-scope list.
6. **Concurrency target of 3 simultaneous requests (§13.2) has not been load-tested** against actual hardware; this MUST be validated against whatever GPU is actually available before the live demo, and the number revised if necessary.

---

## 18. Repository Structure

```
satquery-ai/
├── docker-compose.yml
├── config/
│   └── config.yaml                 # thresholds, adapter version pins, routing table source
├── frontend/
│   └── src/
│       ├── pages/UploadQuery.tsx
│       ├── pages/Results.tsx
│       ├── components/EvidenceOverlay.tsx
│       ├── components/ExecutionTracePanel.tsx
│       └── components/ConfidenceBadge.tsx
├── services/
│   ├── api_gateway/
│   │   ├── main.py                 # FastAPI app, routes §9
│   │   └── schemas.py              # Pydantic models mirroring §8
│   ├── orchestrator/
│   │   ├── query_interpreter.py    # §4.1
│   │   ├── compatibility_validator.py  # §4.2
│   │   ├── specialist_router.py    # §4.3
│   │   ├── verifier_node.py        # §7.1
│   │   ├── confidence_scorer.py    # §7.2
│   │   ├── trace_emitter.py        # §7.3
│   │   └── response_composer.py
│   ├── fusion_pipeline/
│   │   ├── evidence_extraction.py  # sub-step 1
│   │   ├── complementarity_detector.py  # sub-step 2 (+ rule-based fallback)
│   │   └── verbalizer.py           # sub-step 3
│   ├── report_service/
│   │   └── render.py               # PDF/JSON export, §9.6
│   └── model_serving/
│       ├── serve.py                # vLLM/HF endpoint, adapter hot-swap §5.4
│       └── adapters/                # LoRA weight directories, §10.3
├── training/
│   ├── data_prep/
│   │   ├── reben_ingest.py
│   │   └── score_rs_filter.py      # §11.1.1
│   ├── train_vqa_caption.py        # §11.2
│   ├── train_grounding.py          # §11.2
│   ├── train_change_vqa.py         # §11.3
│   └── domain_gap_augmentation.py  # §11.4
├── eval/
│   ├── run_vrsbench_eval.py
│   ├── run_rsvqa_eval.py
│   ├── run_cdvqa_eval.py
│   └── run_finetune_delta_ablation.py  # §16.3
├── tests/
│   ├── unit/  (mirrors §16.1)
│   └── integration/  (mirrors §16.2)
└── docs/
    ├── SatQuery_AI_Final_Synthesized_Solution.md   (proposal doc)
    └── SatQuery_AI_SPDD.md                          (this document)
```

---

## 19. Glossary

| Term | Definition |
|---|---|
| **Adapter** | A LoRA weight delta for one specialist task, applied on top of the shared frozen backbone. |
| **Compatibility Validator** | The orchestration node that structurally checks a `TaskSpec` against image metadata and specialist preconditions before any model runs. |
| **Evidence Ledger** | The structured, in-memory/persisted collection of all specialist outputs for one session, consumed by the verifier and confidence scorer. |
| **Execution Trace** | The mandatory, auditable, structured log of every orchestration step, tool, parameter, and output for one session. |
| **GSD** | Ground Sample Distance — the real-world size represented by one pixel. |
| **Precondition block** | A specialist's static, machine-readable requirements (image count, modality, temporal/spatial constraints) used by the Compatibility Validator. |
| **Task Spec** | The structured output of the Query Interpreter, representing the parsed intent of a natural-language query. |
| **Task token** | A short literal string (e.g., `[vqa]`) prepended to an instruction to signal task identity to the shared backbone, redundant with adapter selection. |

---

## 20. Appendix — Sequence Walkthroughs

### 20.1 Single-image VQA (happy path)

```
User → frontend: uploads 1 optical image + "What land-cover types are visible?"
frontend → api_gateway: POST /v1/analyze (multipart)
api_gateway → object_store: store image, compute contentHash
api_gateway → orchestrator: AnalyzeRequest
orchestrator → query_interpreter: query text + image context
query_interpreter → orchestrator: TaskSpec{taskType: single_vqa, intentConfidence: 0.92}
orchestrator → compatibility_validator: TaskSpec + ImageMetadata
compatibility_validator → orchestrator: ValidationPass
orchestrator → specialist_router: TaskSpec
specialist_router → orchestrator: [vqa_caption_specialist]
orchestrator → vqa_caption_specialist → model_serving(adapter=adapter_vqa_caption, task=[vqa])
model_serving → orchestrator: answerText, rawTokenConfidence
orchestrator → verifier_node: EvidenceLedger (1 item)
verifier_node → orchestrator: annotated ledger (all checks pass)
orchestrator → confidence_scorer: → tier=Medium (MVP default path, rule 5)
orchestrator → trace_emitter: ExecutionTrace (1 step)
orchestrator → response_composer: AnalyzeResponse
api_gateway → metadata_db: persist session
api_gateway → frontend: AnalyzeResponse
```

### 20.2 Compound query — "use optical and SAR together to identify built-up regions, then tell me if built-up area increased since the last pass" (fusion_then_change)

```
query_interpreter → TaskSpec{taskType: fusion_then_change, requiredImageCount: 3+ (fusion pair + prior-date reference), ...}
```
*(Note: this specific compound query implies THREE images — an optical+SAR same-time pair AND a prior-date reference — which is beyond the PS's core two-image-pair scope. The Compatibility Validator MUST detect this and, per §14.1's `insufficient_image_count` code, either request the third image explicitly via a clarifying question, OR — if only 2 images are supplied — decompose the request into what IS answerable (fusion only) and state the limitation in the answer text rather than silently ignoring the "since the last pass" clause. This exact case is flagged here because it is the kind of query-vs.-input mismatch the Compatibility Validator exists to catch, and it MUST be covered by an integration test per §16.2.)*

```
[assuming 2 images supplied: optical + SAR, same time — validator passes for "fusion" only]
compatibility_validator → orchestrator: ValidationPass (taskType downgraded to "fusion"; orchestrator appends a note that the temporal-comparison clause cannot be satisfied with the supplied inputs)
orchestrator → specialist_router → [fusion_pipeline]
orchestrator → fusion_pipeline → (sub-steps 1-3, §6) → regionTags, answerText
orchestrator → verifier_node → confidence_scorer → trace_emitter → response_composer
response_composer: answerText explicitly states "Built-up regions identified from the optical-SAR pair; a prior-date reference image is required to assess whether built-up area has increased — none was supplied."
```

### 20.3 Rejected query — mismatched footprints

```
query_interpreter → TaskSpec{taskType: change_vqa, ...}
compatibility_validator: footprint overlap = 12% (< 70% threshold)
compatibility_validator → orchestrator: ValidationRejection{reasonCode: insufficient_footprint_overlap, humanReadableReason: "These two images cover different geographic areas..."}
orchestrator → trace_emitter: ExecutionTrace{rejection: {...}}  // trace still emitted, even on rejection
orchestrator → response_composer: AnalyzeResponse{rejected: true, rejectionReason: "..."}
api_gateway → frontend: renders the Rejection card (§12.1)
```
