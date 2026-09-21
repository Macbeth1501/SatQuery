# SatQuery AI — Development & Implementation Plan

**Project ID:** SIH26167
**Project:** SatQuery AI — An Interactive Vision-Language Assistant for Multimodal
Remote Sensing Image Analysis through Text Queries
**Target:** A hackathon-ready interactive web prototype built on deterministic dummy
models, preserving the architecture and contracts that real models will later slot into.

---

## 0. About This Document

This is the single roadmap for building SatQuery AI. It merges two earlier documents:

- `SatQuery_AI_Hackathon_Development_Plan.md` — product philosophy, UX specification,
  dummy-model design and the phased delivery roadmap.
- `SatQuery_AI_Implementation_Plan.md` — the module/step/sub-step task breakdown across
  Frontend, Backend and AI/ML, with cross-domain dependencies and flagged ambiguities.

They overlapped but did not agree. Where they conflicted, this document resolves the
conflict in favour of **what is actually built** and records the resolution in
[Appendix B](#appendix-b--reconciliation-of-the-two-source-plans).

### Source of truth

These remain authoritative and are not superseded by this plan:

1. `Problem_Statement.md` — required capabilities and evaluation scope.
2. `SatQuery_AI_Final_Synthesized_Solution.md` — selected architectural principles and
   major technical decisions.
3. `SatQuery_AI_SPDD.md` — build-ready component contracts, API structures, frontend
   requirements, validation rules, specialist interfaces, evidence model, confidence
   logic, deployment approach and testing strategy.

**Do not redesign the project independently when implementing this plan.**

For current build state, see `PROGRESS_LOG.md`. This document is the plan; the log is
the status.

### Status markers

Module and phase headings carry a status marker:

| Marker | Meaning |
|---|---|
| **DONE** | Built and verified against the test suite |
| **PARTIAL** | Built in a reduced or stubbed form; the gap is stated |
| **TODO** | Not started |

### How the module breakdown works

- Work splits into three **domains**: Frontend (`F0…F9`), Backend (`B0…B17`), AI/ML
  (`M0…M11`), designed so different people on different machines can work with minimal
  merge conflicts.
- Every module states its **dependencies** explicitly, including cross-domain ones.
  Modules with no dependency on unfinished work can start immediately.
- The first module in each domain (`F0`, `B0`, `M0`) is setup-from-scratch and must land
  before the rest of that domain begins.
- **FLAGGED** call-outs mark places where the Problem Statement, Proposal and SPDD
  conflict, are silent, or leave a choice unresolved. They are surfaced, not silently
  decided. All of them are collected in
  [Appendix A](#appendix-a--flagged-ambiguities--gaps).

---

## 1. Product Goal

Build a polished interactive web application in which a user can:

- Upload one or two remote-sensing images.
- Enter a natural-language query.
- Let the system determine the appropriate analytical task.
- Validate whether the uploaded inputs are compatible with that task.
- Route the request to the appropriate specialist workflow.
- Run a dummy specialist implementation initially.
- Produce structured evidence.
- Verify the evidence.
- Generate a High / Medium / Low confidence result.
- Display an auditable execution trace.
- Return a grounded textual answer with visual evidence.
- Download a PDF / JSON report.

The prototype must look and behave like the intended final system even though the first
implementation uses deterministic dummy models.

---

## 2. Core Product Philosophy

### 2.1 Validate before execute

The Compatibility Validator is a first-class stage. It determines whether the query can
actually be answered from the supplied image configuration **before** specialist
execution begins. Invalid or unsatisfiable requests produce a polished rejection state
with a human-readable explanation — never a generic error.

### 2.2 Typed, deterministic orchestration

No free-form runtime model selection. The Query Interpreter converts the query into a
structured `TaskSpec`; the Specialist Router then uses a fixed, testable routing table.

### 2.3 Evidence before final answer

Specialists produce structured evidence. The verifier evaluates the collected evidence
before the final answer is shown.

### 2.4 Confidence must be explainable

High / Medium / Low with a short rationale. Never present a meaningless raw probability
as if it were calibrated truth.

### 2.5 Dummy models must be replaceable

Every dummy specialist exposes the same logical interface and output structure a future
real specialist will use. **The frontend must never depend on whether the backend is
using a dummy or real model.**

---

## 3. Supported User Input

### 3.1 Single image

One optical/multispectral image, or one SAR image.
Tasks: VQA, captioning / scene description, text-guided grounding.

### 3.2 Optical + SAR pair

Two co-registered images, one optical/multispectral and one SAR.
Task: optical-SAR joint analysis / fusion.

### 3.3 Bi-temporal pair

Two spatially corresponding observations from different times.
Tasks: change description, change-VQA, change + grounding.

### 3.4 Supported formats

GeoTIFF, TIFF, and PNG/JPEG for benchmark and demo scenarios. The implementation
preserves the distinction between georeferenced raster inputs and ordinary image files.

---

## 4. Target User Journey

```text
User Input
    |
    v
Query Interpreter
    |
    v
Compatibility Validator
    |
    v
Specialist Router
    |
    +-------------------------------+
    |               |               |
    v               v               v
   VQA          Grounding       Change-VQA
    |               |               |
    +---------------+---------------+
                    |
                    v
              Fusion Pipeline
                    |
                    v
             Evidence Verifier
                    |
                    v
             Confidence Scorer
                    |
                    v
              Trace Emitter
                    |
                    v
             Response Composer
                    |
                    v
       Answer + Visual Evidence
       + Confidence + Trace + Report
```

Compound workflows run `Fusion -> Change-VQA` or `Change-VQA -> Grounding`.

---

## 5. Application Structure

### 5.1 Frontend — DONE

React, TypeScript, Vite. Routes:

```text
/          Landing / Home
/analyze   Upload & Query
/results   Results Dashboard
```

The processing view is a full-screen state on `/analyze` rather than its own route, which
the plan permits — but the application must visibly show the stages being executed.

### 5.2 Backend — DONE

Python, FastAPI, Pydantic. Logical components, all present under `backend/app/`:

```text
api (routes_analyze, routes_session, routes_system)
orchestrator/orchestrator_service
orchestrator/query_interpreter
orchestrator/compatibility_validator
orchestrator/specialist_router
orchestrator/verifier_node
orchestrator/confidence_scorer
orchestrator/trace_emitter
orchestrator/response_composer
specialists/vqa_caption
specialists/grounding
specialists/change_vqa
fusion_pipeline/complementarity_detector
fusion_pipeline/verbalizer
services/report_service
services/storage_service
services/metadata_service
services/overlay_service
```

### 5.3 Model layer — PARTIAL

Current implementation is deterministic and dummy:

```text
dummy_vqa_caption      -> specialists/vqa_caption.py    (ScenarioEngine lookup)
dummy_grounding        -> specialists/grounding.py      (ScenarioEngine lookup)
dummy_change_vqa       -> specialists/change_vqa.py     (ScenarioEngine lookup)
dummy_fusion           -> fusion_pipeline/              (ScenarioEngine lookup)
```

Future implementation replaces each with `real_*`. **The orchestrator must not care which
implementation is active.**

---

## 6. Frontend Product Plan

### 6.1 Landing page — DONE

Explains the product in a few seconds. Contains SatQuery AI branding, a short
description, a Start Analysis CTA, and four capability callouts: Multimodal Analysis,
Agentic Intelligence, Evidence Grounding, Confidence / Trace / Reporting. Do not overload
the page with technical documentation.

### 6.2 Upload & Query page — DONE

**Image upload area.** Image 1, optional Image 2, drag and drop, file picker,
remove/replace, preview, file metadata summary.

**Metadata summary.** Format, modality, resolution / GSD, CRS, acquisition date, image
dimensions. For the dummy demo, metadata may be inferred from file properties or demo
configuration.

**Natural-language query.** A large input box, with the Problem Statement's own
representative queries as rotating examples:

```text
Describe the land-cover and major objects visible in this image.
Highlight the water body referred to in the query.
What changed between these two dates, and where did the change occur?
Use the optical and SAR images together to identify built-up and water-covered regions.
Has the built-up area increased, decreased, or remained unchanged?
```

**Capability hint panel.** Lists VQA, Captioning, Grounding, Change Analysis, Optical-SAR
Fusion, Compound Analysis, and makes clear which the current input configuration can
support. If the registry call fails, hide the panel silently — it is a hint, not a gate.

### 6.3 Processing / agent view — DONE

An important part of the demo. Displays observable execution steps:

```text
1. Query received
2. Query interpreted
3. Input compatibility checked
4. Specialist workflow selected
5. Specialist execution
6. Evidence verification
7. Confidence estimation
8. Response composition
```

Each step carries a state: Pending, Running, Completed, Rejected, Failed.

**Do not expose hidden chain-of-thought or internal reasoning.** Only observable system
operations, tools, parameters, outputs and status.

### 6.4 Results dashboard — DONE

The most important demo screen. Two-column layout.

**Left / main area.**
- *Answer* — final answer plus a short explanation.
- *Visual evidence* — original image, annotated image, bounding boxes, change mask where
  available, evidence regions, overlay toggles. For grounding, if multiple candidate
  regions are returned, **show all plausible candidates** rather than a silent top-1.

**Right / supporting area.**
- *Confidence* — tier plus rationale, e.g.
  `LOW — Deterministic quantity check disagrees with the specialist result.`
- *Task information* — selected task, image count, modalities, temporal relationship.
- *Verification* — geometric consistency, cross-tool agreement, quantity validation.
- *Execution trace* — collapsible; step number, component, specialist/adapter,
  parameters, runtime, output summary.
- *Reports* — Download PDF, Download JSON.

### 6.5 Rejection state — DONE

A rejection is not a generic error toast. It is a dedicated, polished state:

```text
INPUT COMPATIBILITY CHECK

Change analysis cannot be performed.

Detected:
Image 1 → Optical
Image 2 → SAR

Required:
Two spatially corresponding observations
from the same modality for temporal change analysis.

Suggested action:
Use T1 + T2 images for change analysis,
or ask an Optical-SAR analysis question.
```

This is a key demo feature.

---

## 7. Component Contracts

### 7.1 Query Interpreter — DONE

Converts natural language into a structured `TaskSpec`. Supported task types:

```text
single_vqa            change_vqa              fusion
single_caption        change_description      fusion_then_change
single_grounding      change_and_grounding
```

If the interpreter cannot confidently map an input it returns an ambiguous state or
requests clarification rather than inventing an unsupported task. The SPDD sets the
ambiguity threshold at `intentConfidence < 0.55`.

### 7.2 Compatibility Validator — DONE

Deterministic, non-LLM. Checks image count, modality, format, CRS, temporal relationship,
spatial overlap, required metadata and specialist preconditions.

| Input | Query | Result |
|---|---|---|
| 1 optical image | VQA query | PASS |
| 1 image | change query | REJECT |
| Optical + SAR | same-modality temporal change query | REJECT |
| Optical + SAR | optical-SAR analysis query | PASS |

Validation runs in this order: format sniff → modality detection → count check → pair
checks (CRS, footprint overlap, temporal ordering) → radiometric sanity (warn, do not
reject) → rejection construction using the SPDD §14.1 templated strings. Never leak a raw
exception message into a response.

### 7.3 Specialist Router — DONE

A deterministic mapping. The router must not invent runtime task names.

```text
single_vqa           -> vqa_caption_specialist
single_caption       -> vqa_caption_specialist
single_grounding     -> grounding_specialist
change_vqa           -> change_vqa_specialist
change_description   -> change_vqa_specialist
change_and_grounding -> change_vqa_specialist -> grounding_specialist
fusion               -> fusion_pipeline
fusion_then_change   -> fusion_pipeline -> change_vqa_specialist
```

A CI test must assert `set(ROUTING_TABLE.keys()) == set(TaskType values)` so the schema
and the table cannot drift.

### 7.4 Specialist output contracts — DONE

**VQA / Captioning.** Accepts one image, a query and a mode (`vqa` | `caption`):

```json
{
  "answerText": "string",
  "answerType": "open_ended | binary | mcq",
  "boundingBoxesIfAny": [],
  "rawTokenConfidence": 0.0
}
```

**Grounding.** Accepts one optical/multispectral image and a referring expression:

```json
{ "boxes": [], "isAmbiguous": false, "candidateCount": 1 }
```

Must be able to return one candidate or multiple plausible candidates, to demonstrate
ambiguity handling. Never silently collapse to top-1.

**Change-VQA.** Accepts image T1, image T2 and a query:

```json
{
  "answerText": "string",
  "changeMaskAvailable": true,
  "changeMaskRef": "string | null",
  "quantityFlag": false,
  "deterministicPixelCount": null
}
```

For quantity-style queries, populate the deterministic cross-check fields so the verifier
can demonstrate discrepancy handling.

**Fusion pipeline.** Preserves the structured fusion concept:

```text
Optical image ──> Independent evidence extraction ──┐
                                                     ├──> Complementarity
SAR image     ──> Independent evidence extraction ──┘      Detection
                                                                │
                                                                v
                                                        Evidence Fusion
                                                                │
                                                                v
                                                         Verbalization
```

The complementarity detector may be rule-based initially; its interface must remain
replaceable by the future learned detector. The verbalizer **must not be given raw
pixels** — only the structured, already-tagged comparison.

### 7.5 Evidence model — DONE

All specialists contribute to a structured ledger:

```text
EvidenceLedger
├── specialist outputs
├── bounding boxes
├── masks
├── region tags
├── deterministic counts
├── geometry validity
├── agreement flag
└── discrepancy flags
```

Feeding `Verifier -> Confidence -> Response Composer`.

Bounding boxes are always 0–100 normalized percentages (`normalizedTo100: true`).

### 7.6 Verification — DONE

*Geometric checks* — boxes inside image bounds, change region inside the valid overlap,
valid oriented-box angle.
*Cross-tool agreement* — where independent evidence sources exist, compare and identify
agreement/disagreement.
*Quantity validation* — for quantity-style questions, compare the model's answer-derived
quantity against the deterministic evidence and flag material discrepancies.

**The verifier annotates the evidence; it never silently rewrites the model answer.** This
invariant deserves its own dedicated test.

> **Implementation note.** The quantity check only runs for genuine counting questions and
> treats a claim as consistent if any integer in the answer matches the feature count.
> An earlier version took the first integer in the text, which read list markers such as
> `"1) Marine Port Basin"` as a claimed count and forced every demo to Low confidence.

### 7.7 Confidence system — DONE

MVP path, first applicable rule wins:

```text
If geometry fails            -> LOW
Else if quantity discrepancy -> LOW
Else if known weak query     -> one-tier discount
Else                         -> MEDIUM / HIGH per scenario calibration
```

The SPDD's full five-rule list adds Rule 4 (decoupled perception/reasoning confidence
tokens above calibration threshold → High) as a stretch goal. Implement as a literal
ordered `if/elif` chain, not a scoring/summation system — that would violate the
documented design intent. If the stretch-goal tokens are absent, Rule 4 simply never
matches and the chain falls through. Prioritise the simple auditable path.

### 7.8 Execution trace — DONE

Every important operation generates a trace entry:

```json
{
  "stepIndex": 3,
  "component": "specialist_router",
  "adapterIdOrVersion": null,
  "parametersUsed": { "taskType": "change_vqa" },
  "wallClockMs": 20,
  "outputSummary": "Selected change_vqa_specialist"
}
```

The frontend renders this as a timeline. **A trace is emitted even on rejection**, with
the rejection reason in place of the step body, and including the steps that did run
before the short-circuit.

### 7.9 Report generation — DONE

*PDF* must include title, session ID, query, input information, detected task, final
answer, evidence images, confidence, confidence rationale, verification results and the
execution trace. *JSON* returns the structured `AnalyzeResponse` / session information.
The report must contain the same information shown on the Results page.

`?format=pdf` returns a rendered PDF, `?format=html` the printable HTML, and
`?format=json` the structured response. The PDF is rendered once per session and
cached; a rejected session returns `409`, since it produced no analysis to report.

Rendering uses `xhtml2pdf`, which is pure Python. WeasyPrint and wkhtmltopdf were
both rejected because they need native GTK or Qt libraries that a demo machine
would have to install separately — an avoidable failure mode on presentation day.

### 7.10 API contract principle — DONE

```text
Frontend --AnalyzeRequest--> Backend --AnalyzeResponse--> Frontend
```

The frontend must never branch on something like `if task == dummy_change_model`. It
consumes only the standard response fields: `answerText`, `evidence`, `confidence`,
`executionTrace`, `reportUrl`, `rejected`, `rejectionReason`. This is what lets real
models replace dummy models without redesigning the frontend.

**Naming convention:** camelCase on the wire and in TypeScript, snake_case inside Python,
bridged by a Pydantic `alias_generator` with `populate_by_name=True`.

---

## 8. Dummy Model Design

The dummy models must be deterministic enough for a live demo. **Do not return random
text.** They live in a small Scenario Engine, isolated from orchestration.

| # | Scenario | Input | Query | Expected output |
|---|---|---|---|---|
| A | VQA | 1 optical | *Describe the land-cover and major objects visible in this image.* | Land-cover narrative + object boxes |
| B | Grounding | 1 optical | *Highlight the water body referred to in the query.* | Answer text, one or more boxes, annotated image |
| C | Change | T1 + T2 | *What changed between these two dates, and where did the change occur?* | Change description, region/mask, evidence image, confidence |
| D | Optical-SAR Fusion | Optical + SAR | *Use the optical and SAR images together to identify built-up and water-covered regions.* | Optical evidence, SAR evidence, complementarity result, combined answer |
| E | Compound | Optical + SAR | *…identify built-up areas, then determine whether the built-up area increased.* | Fusion → Change-VQA → Verifier → Confidence → grounded response |

### 8.1 Demo mode — DONE

A visible **Demo Scenarios** section with buttons:

```text
[ Scene Understanding ] [ Grounding ] [ Change Detection ]
[ Optical + SAR ] [ Fusion → Change ] [ Validation / Rejection ]
```

Selecting a scenario pre-loads the appropriate demo images and query, guaranteeing
repeatable live demonstrations.

---

## 9. Delivery Phases

```text
PHASE 0  Understand + Freeze Plan
   ↓
PHASE 1  Frontend Foundation
   ↓
PHASE 2  FastAPI + Contracts
   ↓
PHASE 3  Agentic Orchestration
   ↓
PHASE 4  Scenario-Aware Dummy Models
   ↓
PHASE 5  Evidence + Results Dashboard
   ↓
PHASE 6  Validation + Rejection
   ↓
PHASE 7  Reports + Demo Polish
   ↓
PHASE 8  Full Integration + Testing
   ↓
REAL MODEL INTEGRATION
```

| Phase | Objective | Exit criteria | Status |
|---|---|---|---|
| **0** — Document study | Understand the three source documents and freeze the plan. No code. | Team can explain what the PS requires, what the solution adds, what the SPDD specifies. | DONE |
| **1** — Frontend foundation | Build the visual product shell: landing, upload & query, results skeleton, header, upload, preview, query box, example queries, capability hints, loading state. | All routes work, no major console errors, no backend required. | DONE |
| **2** — FastAPI + contracts | FastAPI app, Pydantic schemas, `/v1/analyze`, `/v1/session/{id}`, `/v1/session/{id}/report`, `/v1/health`, `/v1/registry`. | Frontend can send an analyze request and receive a structurally valid `AnalyzeResponse`. | DONE |
| **3** — Agentic orchestration | The complete logical pipeline on dummy services: Interpreter → Validator → Router → Specialist → Verifier → Confidence → Trace → Response. | At least one end-to-end request works through the complete pipeline. | DONE |
| **4** — Scenario-aware dummies | VQA, caption, grounding, change-VQA, fusion, compound fusion + change. | All five demo scenarios produce deterministic, structured results. | DONE |
| **5** — Evidence & dashboard | Annotated images, boxes, change regions, optical/SAR comparison, evidence cards, confidence, verification results, trace panel. | A judge can understand exactly what was analyzed and why the answer was produced. | DONE |
| **6** — Compatibility & rejection | Input compatibility checks, human-readable rejection state, suggested corrective action, validation trace. | Invalid combinations fail gracefully without crashing. | DONE |
| **7** — Reports & polish | PDF report, JSON export, loading animations, transitions, empty states, proper failures, responsive layout, professional styling, demo mode. | A complete live demo runs without manual backend manipulation. | DONE |
| **8** — Integration & validation | End-to-end readiness pass across all task types, rejection, confidence, trace, PDF, JSON. | All critical demo paths work from the browser. | DONE — 106 pytest + 55 Vitest tests |

---

## 10. Module Breakdown

### 10.1 Cross-domain dependency overview

```text
B0 (repo/env setup) ──────────────┬─────────────────────────────┐
                                   │                              │
M0 (data pipeline setup) ─────────┼──> M1 (model serving infra)  │
                                   │        │                     │
F0 (frontend setup) ───────────────────────┼─────────────────────┤
                                            │                     │
B1 (data contracts/schemas) ───────────────┼──> B2 (API gateway) │
                                            │        │            │
                              M2 (query interpreter model)        │
                                       │                          │
                        B5 (query interpreter integration) <──────┘
                                       │
                        B6 (compatibility validator) <── M9 (modality heuristic)
                                       │
                        B7 (specialist router)
                                       │
        M3/M4/M5 (adapters) ──> B8 (specialist invocation layer)
                                       │
        M7/M8 (fusion) ──> B9 (fusion orchestration)
                                       │
                        B10 (verifier) ──> B11 (confidence) ──> B12 (trace) ──> B13 (response composer)
                                       │
                        B14 (report service)      F2..F8 (frontend pages)
                                       │
                        B17 (deployment wiring) <── F-all, B-all, M1
```

### 10.2 Frontend modules

| Module | Purpose | Depends on | Status |
|---|---|---|---|
| **F0** Project setup | Vite + React + TS skeleton, folder structure, router, lint baseline. | — | DONE |
| **F1** API types & client | TypeScript mirrors of the SPDD §8 contracts in one `types.ts`; one client function per endpoint; a normalized error result distinguishing `400` / `503` / network failure. | F0, logically B1 | DONE |
| **F2** Upload & query page | Drop-zone accepting 1–2 files with client-side extension/count checks (UX pre-check only — the server remains the authority); query box; capability hints from `/v1/registry`; submit handler with elapsed-time feedback. | F0, F1 | DONE |
| **F3** Results core | Page shell, answer panel, confidence badge (green/amber/red + visible rationale). Early-returns to F6 when `rejected`. | F0–F2 | DONE |
| **F4** Evidence overlay | Base image plus absolutely-positioned overlay; convert 0–100 coordinates to pixels; honour `theta`; render **all** grounding candidates with score-varied styling; per-layer toggles; layer server-rendered change masks without client-side vectorization. | F0, F1, F3 | DONE |
| **F5** Execution trace panel | Collapsible, open by default; step table; confidence tier and rationale repeated for a self-contained screenshot; handles the rejection-trace case where `steps` may be short. | F0, F1 | DONE |
| **F6** Rejection state | A visually distinct card — informative, not alarm-red, since rejection is correct behaviour. Displays the reason verbatim, never paraphrased. Trace still renders below it. | F0, F1 | DONE |
| **F7** Map integration | Leaflet `MapContainer` when CRS/footprint metadata is present; plain image viewer otherwise. Use `L.CRS.Simple`; never pull public basemap tiles, which would violate the offline NFR. | F0, F1, F4 | TODO |
| **F8** Report download & session reopen | PDF/JSON download via `<a href download>` so the browser streams the file; hide the button entirely when `rejected`; support direct navigation to a session URL with a distinct not-found state. | F0, F1 | DONE — `/results/:sessionId` with loading, Session Not Found and Could Not Load states (A8). Reopened sessions show no source imagery until `inputImages` is added |
| **F9** Frontend testing | Component tests (badge colours, multi-box rendering, rejection-trace branch, verbatim rejection text) and page-level tests against a mocked client. | F0–F8 | DONE — 55 Vitest tests, including demo-scenario parity with the backend |

### 10.3 Backend modules

| Module | Purpose | Depends on | Status |
|---|---|---|---|
| **B0** Repo & environment | Repository layout, Python dependency baseline, externalized config, container skeleton, CI skeleton. | — | PARTIAL — layout, `requirements.txt` and externalized config (A4) exist; containers and a CI workflow now exist (Track D); tests and lint run in CI |
| **B1** Data contracts | Pydantic models for every SPDD §8 schema, with `Literal` enums and the camelCase alias generator. Schema tests assert round-trip field names match the SPDD exactly. | B0 | DONE |
| **B2** API gateway core | FastAPI app, CORS for the dev origin, the five endpoints. Enforce `1 <= len(images) <= 2` and non-empty query with HTTP 400. | B0, B1 | DONE |
| **B3** Object store | Storage abstraction over the SPDD §10.1 path convention; SHA-256 content hashing for the embedding cache. | B0 | PARTIAL — local filesystem with hashing; no cache layer |
| **B4** Metadata DB | Three-table relational schema (`sessions`, `evidence_ledgers`, `execution_traces`), migrations, repository functions. | B0, B1 | DONE — SQLite via stdlib `sqlite3` (A3); Postgres/Alembic not used |
| **B5** Query interpreter integration | Call the interpreter model, validate against `TaskSpec`, retry once with a repair prompt on validation error, raise a typed error on second failure. Ambiguous status returns without proceeding to B6/B7. | B1, B0, M2 contract | PARTIAL — deterministic keyword classifier, no model call or retry |
| **B6** Compatibility validator | Precondition table shared with `/v1/registry` so they cannot drift; the six ordered validation steps; compound-task nuance; exhaustive unit tests, one per rejection code. | B1, B0, M9 | DONE |
| **B7** Specialist router | Transcribe the routing table; pure `route()` function, no I/O; CI consistency invariant against the `TaskType` enum. | B1 | DONE |
| **B8** Specialist invocation | Per-specialist call wrappers preserving multi-box and quantity fields untouched; strict sequential execution for dependent compound plans; distinguish "specialist errored" from "model serving is down"; assemble the `EvidenceLedger`. | B1, B7, M1/M3/M4/M5 | PARTIAL — in-process dummy calls, no HTTP/timeout layer |
| **B9** Fusion orchestration | Per-modality evidence extraction, complementarity detector call with a `trained` / `rule_based` config switch at a single call site, verbalization on structured tags only, domain-gap preprocessing hook. | B8, B1, M7, M8 | PARTIAL — rule-based only; no config switch or preprocessing hook |
| **B10** Verifier node | The three check classes; non-mutating contract; six fixtures minimum. | B1, B8, B9 | DONE |
| **B11** Confidence scorer | The priority-ordered rule list as a literal first-match chain; defensive Rule 4 fallback. | B1, B10 | DONE |
| **B12** Trace emitter | A `TraceBuilder` threaded through every orchestrator stage; rejection path; finalization once confidence is known. | B1 | DONE |
| **B13** Response composer | Compose `answerText` (including stating any clause the inputs could not satisfy), assemble `AnalyzeResponse`, render evidence overlays server-side, persist and return. | B1, B10–B12 | DONE |
| **B14** Report service | JSON export direct from the persisted response; PDF via an HTML template; cache the rendered file; `404` for unknown session, `409` for a rejected one; content-parity test against the Results page fields. | B1, B4, B13 | DONE |
| **B15** Registry finalization | Import the precondition table directly rather than re-transcribing; single authoritative source for adapter versions. | B6, M1, B2 | PARTIAL — static catalog, not imported from B6 |
| **B16** Backend testing | Consolidated unit suite plus five end-to-end integration scenarios: clean single-image VQA; a malformed pair parametrized across every rejection code; an ambiguous-referent grounding asserting multiple boxes; a quantity discrepancy asserting `Low`; a compound plan asserting sequential order and step count. | B5–B15 | DONE — 106 tests; the five scenarios are covered |
| **B17** Deployment orchestration | Real container definitions, config/env wiring, health-gated startup sequencing, full-stack smoke test confirming no runtime external network calls. | All of B2–B16, M1, F0–F9 | DONE for the system that exists — Dockerfiles, Compose with health-gated start, a CI workflow, an offline test and a 3-concurrent test. CI builds both images, gates on healthchecks, runs an analyze cycle through the stack and confirms a session survives a restart. No model-serving container, because there is no model server; revisit when Track B lands |

### 10.4 AI/ML modules — all TODO

| Module | Purpose | Depends on |
|---|---|---|
| **M0** Data pipeline | Ingest BigEarthNet.txt via reBEN into LMDB/safetensors; honour the **official geographic split**, not a naive grid split, and log which tiles went where; quality-score filter dropping the bottom quartile with `pairs_in`/`pairs_kept` logged to a committed file; acquire fusion-bridging data (CMU-Data, SOMA-1M) into a separate directory so it never mixes with the single-image pool; source domain-shift proxy samples. | — |
| **M1** Model serving | Pin a compact open-weight VLM (1–4B); single parameterized `/infer` endpoint; **adapter hot-swap with all LoRA deltas resident simultaneously** — a hard NFR, since compound queries call two specialists per request; `/health` and `/adapters` introspection; task-token conditioning (`[vqa]`, `[caption]`, `[ground]`, `[change]`, `[fusion]`); self-hosted by default with any hosted-LLM fallback opt-in, never touching image bytes. | M0 |
| **M2** Query interpreter model | Small text-only instruct LLM in JSON/function-calling mode, output constrained to the `TaskSpec` JSON Schema so an out-of-enum `taskType` is structurally impossible. Few-shot exemplars from the PS's own representative queries plus hand-written ambiguous cases. Emit a calibrated `intentConfidence`. | M1 |
| **M3** VQA + captioning adapter | Frozen encoder and decoder; modality-specific projection layers for S1/S2; LoRA rank 8–16 on attention Q/K/V/O only. Evaluate on VRSBench and RSVQA, held out. | M0, M1 |
| **M4** Grounding adapter | Separately tuned — never joint-trained with VQA/captioning, per the documented task-interference collapse. Boxes as tokenized sequences, not a detection head. Multi-candidate output is mandatory. Report Acc@0.5 honestly and always pair a grounding result with its confidence badge. | M0, M1 |
| **M5** Change-VQA adapter | CDVQA ingestion retaining `test2` as the honest reporting split. Siamese T1/T2 encoding with **difference-attention, not naive subtraction**, optimized jointly with the LoRA decoder. Deterministic pixel/instance count computed independently of the text answer — the independence is what makes the downstream cross-check non-circular. Report per-question-category accuracy, not an average. | M0, M1 |
| **M6** Domain-gap mitigation | GSD-normalization tiling and radiometric jitter (histogram matching toward Cartosat-2S, speckle injection matching RISAT), from public sensor specifications. Applied to a held-out slice purely as a stress-test ablation, never mixed into headline numbers. Exposed as an always-on inference-time preprocessing function. | M0 |
| **M7** Complementarity detector | SAR-DINO / RGB-DINO dense-feature encoder pair trained with InfoNCE alignment. Served as its own lightweight endpoint, separate from the LLM. **The single highest-risk deliverable** — communicate a go/no-go early so B9's rule-based fallback is flipped deliberately, with time to verify it. | M0.4, M1 |
| **M8** Fusion composition | Resolve the structured-extraction format jointly with M3/B9; design the verbalizer prompt template so claims are attributed to the supplying modality; build a small self-constructed evaluation set and label it as non-standard. | M3, M7 |
| **M9** Modality detection heuristic | Deliberately *not* a deep model: band count, wavelength tags, pixel-distribution statistics into logistic regression or a shallow tree. Sub-100 ms, CPU-only. A fallback for genuinely ambiguous cases only. | M0 |
| **M10** Evaluation harness | Consolidate per-adapter eval scripts; implement the **fine-tuning delta ablation** (un-adapted backbone vs. trained adapter) as a committed, re-runnable script — the single most judge-legible proof that the mandatory adaptation requirement is met. Persist every run's output. Report literature-cited baselines alongside own numbers. | M3–M5, M0 |
| **M11** Decoupled confidence *(stretch)* | VL-Calibration-style separate perception and reasoning confidence tokens, calibrated on a validation slice (never the test split). Only after M0–M10 are demo-ready. | M3–M5, B11 |

### 10.5 Sequenced execution plan for the remaining work

Sections 10.2–10.4 say *what* each module is. This section says *what to do next, in
what order*, for everything still marked PARTIAL or TODO. Every step names the files it
touches and the condition that closes it.

Work splits into four tracks. **Track A needs no model and can start immediately, in
parallel.** Track B is the ML programme and is gated on two decisions. Track C wires B
into the running system. Track D ships it.

```text
         ┌──────────────────────────────────────────────┐
DECISIONS│ D1 pin backbone model   D2 confirm compute   │
         └───────────────┬──────────────────────────────┘
                         │ (gates Track B only)
TRACK A ────────────────────────────────────────────────────> (independent, start now)
A1 raster metadata   A2 PDF   A3 datastore   A4 config
A5 live/mock honesty A6 map   A7 fe tests    A8 session reopen
                         │
TRACK B                  v
B1 data ─> B2 serving ─> B3 interpreter ─┐
                    └──> B4 modality     │
                    └──> B5 vqa ─┐       │
                    └──> B6 ground┤      │
                    └──> B7 change┤      │
                         B8 domain gap   │
                         B9 detector ────┤ (go/no-go gate)
                         B10 fusion  ────┤
                         B11 eval harness│
                         B12 confidence (stretch)
                                         │
TRACK C  <───────────────────────────────┘  (needs A4 + Track B)
C1 interpreter wiring  C2 invocation layer  C3 fusion orchestration  C4 registry
                         │
TRACK D                  v
D1 containers  D2 config wiring  D3 startup sequencing  D4 smoke test
```

#### Blocking decisions

These gate Track B entirely. Neither is a coding task; both need a human decision, and
nothing in the ML programme should begin until they are closed.

| # | Decision | Why it blocks | Appendix A |
|---|---|---|---|
| **D1** | Pin the backbone VLM: exact model name **and** revision/commit hash. | The training recipe (frozen encoder + frozen decoder + LoRA on attention projections) is backbone-specific in its exact module names. B3, B5, B6, B7 cannot start without it. | #16 |
| **D2** | Confirm actual GPU hardware and budget. | The ~1–2 GPU-days per adapter figure is a planning assumption, not a guarantee. It determines whether three adapters are feasible at all. | #20 |

**D2 — answered 2026-09-20: NVIDIA RTX 3050, 4 GB dedicated VRAM.** The 8 GB of "shared" memory is
system RAM over PCIe and is not usable for training. **This card cannot fine-tune a 2–3B
vision-language model, QLoRA included** — vision models expand each image into many visual tokens, and
activations plus optimiser state exceed 4 GB. The consequence for this plan: **training moves off the
development machine** to a free or cheap cloud GPU (Kaggle provides 2x T4 16 GB), while 4-bit
inference runs locally provided image resolution is capped. The "~1–2 GPU-days per adapter" figure
above should be re-planned against a rented T4/A100, not this card, and M-track steps should assume
cloud training with the adapter weights pulled back for local serving.

> **Measured 2026-09-20, after D2 was closed (the decision above still stands; this is evidence for the
> owner to weigh).** `ml/b5_train_lora.py` ran QLoRA (rank 16, attention q/k/v/o, gradient checkpointing,
> batch 1) on this card without running out of memory. Peak allocated memory: 2,787 MiB at 448 px on random
> examples; **3,072 MiB at 448 px and 3,880 MiB at 672 px on the eight longest captions in the slice**,
> against roughly 3.3 GB free (the desktop holds the rest). Speed at 448 px was about 1.7 s per example
> (about 8.5 hours for the 17,955-example slice). So the assertion "QLoRA cannot fit" is not borne out for a
> single image at these sizes; what remains true is a thin margin at 672 px, no headroom for two-image
> inputs (not tested), and slow throughput. These are runs of 3-4 optimiser steps, not a full training run.

**D1 — decided 2026-09-20: `Qwen/Qwen2-VL-2B-Instruct`** (step up to
`Qwen/Qwen2.5-VL-3B-Instruct` only if measurement shows the 2B is the limiting factor). The first
criterion is **native multi-image input**, because change detection and fusion are two of the four task
families;
Florence-2 and PaliGemma ground very well but are single-image architectures, and forcing an image
pair onto one canvas would destroy the per-image 0–100 normalised box space that the validator,
verifier, overlay service and frontend all assume. Qwen2.5-VL emits boxes natively, and PEFT can keep
several LoRA adapters resident and switch with `set_adapter()`, satisfying the SPDD 13.2 no-reload
rule for compound queries. **Revision pinned 2026-09-20: `895c3a49bc3fa70a340399125c650a463535e71c`**
(Apache-2.0), read from the Hugging Face Hub and then downloaded at exactly that commit, not typed from
memory. Measured local 4-bit results are in the Progress Log (2026-09-20 smoke test).

The second criterion is **resolution, not parameter count**, and it is what selected the 2B over the
3B. On a 4 GB card the binding constraint is how many pixels reach the model: at 4-bit the 2B leaves
roughly 2.5 GB for visual tokens and KV cache against the 3B's ~1.5 GB, and two-image tasks double the
token count. Remote-sensing grounding is pixel-hungry — a vessel or a tank at 0.65 m GSD is a small
object — so a 2B model at adequate resolution is expected to localise better than a 3B model forced to
downsample. Accepted losses: Qwen2.5-VL improved localisation over Qwen2-VL, so the base model starts
weaker at the project's central capability, and there is less headroom on the compound
fusion-then-change path. Both are mitigated by LoRA fine-tuning on in-domain data (RSVQA, VRSBench,
CDVQA), which narrows base-model gaps. The decision is cheap to reverse: same family, same processor
API, same LoRA target module names, so switching is a model ID change plus a re-train.

---

#### Track A — Hardening, no model required

Eight independent work items. None depends on another except where stated, so they can be
picked up in any order or split across people.

**A1 — Real raster metadata — DONE** *(completed B6.1; activated the dormant preconditions)*

Implemented 2026-09-20. The old `metadata_service.py` did not merely guess: it
*fabricated*. Every `.tif` received the CRS `EPSG:32643` whatever it contained, every
optical image a cloud cover of exactly 12%, and GSD was invented from the filename —
which is why the footprint-overlap and CRS rejection paths could never fire on real
input.

1. **Done.** `rasterio` is now a hard dependency.
2. **Done.** CRS, band count, dimensions, GSD in metres (converted from degrees at the
   scene's latitude for geographic CRSs), NoData share and acquisition time are read from
   the file. The filename heuristic remains only as the fallback, and it now matches short
   hints (`sar`, `s1`, `ms`) as whole tokens, so `farms.png` is no longer multispectral and
   `class1.png` no longer SAR. **A fallback never invents a value** — an unknowable field is
   `None`, so the validator treats it as absent rather than as fact.
3. **Done, without shapely.** The footprint is reprojected to lon/lat with
   `rasterio.warp.transform_bounds`, and overlap is the IoU of the two lon/lat bounding
   boxes, computed in `annotate_pair()` once both images are read. That is exact for
   axis-aligned scenes and an approximation for rotated ones; shapely and pyproj were not
   needed. Overlap stays `None` when either image is not georeferenced, so a pair of plain
   PNGs is never rejected for an overlap nobody could measure.
4. **Done, resolving Appendix A #7.** Cloud share is the fraction of valid pixels whose
   mean brightness is at least 78% of the range, over a decimated read. It is **an
   approximation, not a cloud-detection model** — it flags snow, sand and bright roofs and
   misses thin cloud. It is defined **only for 8-bit imagery**: an earlier draft scaled
   16-bit and float data by the image's own 99.5th percentile, which would have flagged
   the brightest few percent of *any* scene as cloud, so for those dtypes the value is
   reported as unknown. SAR always reports 0.
5. **Partly done.** Modality is now read from platform/sensor tags (`Sentinel-1`, `RISAT`,
   and so on) ahead of the filename, and a local engineering CRS is labelled *unresolvable*
   so the `crs_mismatch_unresolvable` rule can act on it. The hook for Track B's learned
   modality heuristic (B4) is not added — nothing calls it yet.

*Done:* a real GeoTIFF pair with under 70% overlap is rejected with
`insufficient_footprint_overlap`; an unresolvable CRS with `crs_mismatch_unresolvable`;
reversed acquisition order with `temporal_ordering_invalid`; and an optical/SAR pair told
apart by metadata alone with `modality_mismatch` — each on a synthetic GeoTIFF, not a
filename. 28 new tests; **23 of them fail against the old fabricating service**.

**A2 — Real PDF export — DONE** *(completed B14 and closed the last Phase 7 gap)*

Implemented 2026-09-20. `xhtml2pdf` replaced the planned WeasyPrint, which needs
native GTK libraries unavailable on the target Windows machine. The report now also
embeds the annotated overlay image and a bounding-box table, which the HTML template
had never carried — without them the content-parity test would have passed against a
report that showed no evidence at all.

1. Add a renderer — `weasyprint` per the original plan.
2. Feed it the existing `render_html_report()` output; the template already carries full
   content parity, so no new template work is needed.
3. Save the result to the session directory and check for it before re-rendering, so
   repeat downloads do not re-render.
4. Return `409` when the session was rejected — there is nothing to report.
5. Write the content-parity test: assert the field set rendered into the PDF context is a
   superset of what `Results.tsx` renders. A field-name comparison, not visual diffing.

*Done:* the endpoint returns `application/pdf` with the overlay image embedded, the
PDF is cached per session, and a rejected session returns 409 for every format.

**A3 — Persistent datastore — DONE** *(completed B4)*

Done 2026-09-20. Sessions now live in SQLite through `backend/app/services/session_repository.py`
(stdlib `sqlite3`, not SQLAlchemy/Alembic — three tables did not justify two dependencies and a
migration framework; all SQL is in that one module). Three tables (`sessions`,
`evidence_ledgers`, `execution_traces`), append-only migrations tracked by `PRAGMA user_version`,
and a refusal to open a newer-schema database. `StorageService` delegates to it, reading the path
from `SATQUERY_DATABASE_PATH`; legacy `response.json` sessions are imported on first read. Images,
overlays and reports stay in the object store. Listing sessions is not exposed over HTTP because
the API has no authentication. Covered by `tests/test_persistence.py`, including a restart test.

**A4 — Externalized configuration — DONE** *(completed B0.3 and B17.2; unblocks Track C)*

Implemented 2026-09-20.

1. **Done, by environment variables** with the `SATQUERY_` prefix and a stdlib loader (no
   new dependency), documented in `.env.example`. Covered: storage root, host, port, CORS
   origins, the three validation thresholds, the optical-cloud cutoff and the high-confidence
   intent threshold. Malformed values fail at startup naming the variable. **Two items in
   the original list were dropped because they do not exist:** the verifier does an *exact*
   quantity match (there is no 15% tolerance), and the interpreter classifies ambiguity by
   keyword (there is no 0.55 confidence threshold). Externalizing a value the code never
   reads would have been decoration.
2. **Done.** `VITE_API_BASE_URL`, defaulting to `http://127.0.0.1:8000`, trailing slashes
   stripped. See `frontend/.env.example`.
3. **Done.** `confidence_scorer.py` still carried `40.0` and `0.85` literals; both now
   come from config. Two hardcoded values were deliberately left: the trace emitter's 42 ms
   floor (fabricated timing; since removed, see the 2026-09-20 trace-timing entry in
   `PROGRESS_LOG.md`) and the synthetic overlay canvas size.

*Done:* no threshold, URL or path is hardcoded outside the config layer. Verified live: a
backend started with only environment variables served on the configured port, created its
storage in the configured directory, and honoured a CORS override — with nothing leaking
into the default store.

**Two behaviour changes to know about.** The dev server now binds to `127.0.0.1` by
default; it previously bound `0.0.0.0` and exposed the API to the whole network. And the
CORS default no longer includes the `*` wildcard, which combined with credentialed requests
is unsafe; the Vite dev origins remain.

**A5 — Live/mock honesty in the UI — DONE** *(no module; a correctness fix)*

Implemented 2026-09-20.

`SatQueryContext.startAnalysis()` catches every API failure and silently serves
`activeScenario.mockResponse`. **The UI is identical whether the backend is up or down**,
which is a demo hazard as much as a debugging one.

1. **Done.** The fallback stays — it protects a live demo — but the context now tracks
   whether a result came from the API or the bundled scenario, and
   `ResultSourceBadge.tsx` shows "Live Backend" or "Demo Data — Backend Unreachable"
   on both the success and rejection views.
2. **Done, by a third route.** Sending no files was not viable: image count drives task
   validation, so a two-image scenario would have been rejected for
   `insufficient_image_count`. Shipping `demo_data/` rasters would have duplicated
   imagery the UI already holds. Instead the client rasterizes the scenario's own
   preview to a real PNG through a canvas and uploads that, so the backend annotates
   exactly the image on screen. If rasterization fails, it falls back to placeholder
   bytes so the image count — and therefore validation — still behaves.
3. **Not done, and the premise was wrong.** The synthetic 640×640 fallback in
   `overlay_service.py` is *not* dead code. It still fires whenever rasterization fails
   and for any upload Pillow cannot open, which is a real case for exotic raster
   formats. It is now covered by its own test rather than removed.

*Done:* the Results page states plainly whether the answer was computed by the backend,
and a decodable upload is annotated in place. **Verified in Chrome, both paths:** with
the backend up, a real 600×400 PNG is uploaded and annotated at 600×400; with it
stopped, the amber "Demo Data — Backend Unreachable" badge appears.

Browser verification also surfaced a pre-existing crash unrelated to A5 —
`EvidenceViewer` threw on `regionTags: null`, taking down the whole Results page for
every live non-fusion analysis. Fixed alongside. It argues strongly for bringing **A7**
(frontend tests) forward: the Python suite cannot see a render failure.

**A6 — Map layer** *(completes F7; depends on a contract change)*

1. **First resolve Appendix A #3.** `AnalyzeResponse` carries no CRS or footprint, so the
   frontend cannot tell whether to render a map. Add an explicit `hasGeoreference`
   boolean or the footprint itself — do not infer it from overlay URL formatting.
2. Render a Leaflet `MapContainer` with `L.CRS.Simple` and the base image as an
   `ImageOverlay` when georeferencing is present.
3. **Never pull public basemap tiles** — that would violate the offline NFR.
4. Reuse the existing box coordinate conversion rather than duplicating it; extract it to
   a shared utility first.

*Done when:* a georeferenced input renders on a map and a plain PNG renders in the plain
viewer, from the same component tree.

**A7 — Frontend tests — DONE** *(completed F9)*

Implemented 2026-09-20, brought forward from the "whenever there is slack" bucket after
browser verification found a crash the Python suite could not see.

1. **Done.** Vitest + React Testing Library + jsdom, with `npm test` (single run) and
   `npm run test:watch`. Appendix A #14 is resolved by this choice.
2. **Done.** Component tests: badge colour per tier, the rationale stays visible, and
   `details: null` does not throw; every grounding candidate renders with its score;
   region tags appear only when the task produced them; the rejection reason renders
   verbatim with its code, detected-versus-required context and corrective action.
   **One deviation from the plan:** F5.3 said a rejected trace should show the reason
   *instead of* the step table. The component instead shows the steps that ran and
   marks the rejected one, which is what B12.4 recommends ("include the steps that DID
   run") and is the better behaviour — a judge sees that interpretation succeeded
   before the validator halted. The test pins the implemented behaviour; F5.3's wording
   is the document that was wrong.
3. **Done, in part.** Page tests: the empty state; the success, rejection and fusion
   branches each render the right top-level view; the submit button is disabled with no
   image or an empty query and enabled with both. **Not covered:** the three-file drop
   error, which lives inside `ImageUploader`'s file-input handling and is the next
   frontend test to write.

   The fixtures use `null` exactly where the API sends `null` (`regionTags` on every
   non-fusion task, `confidence.details` on a rejection). A fixture using `undefined`
   would let default parameters hide the very bug these tests exist to catch.

   **Mutation-checked:** reintroducing the original `regionTags` crash makes 6 tests fail,
   including the page-level one; restoring the fix returns all 26 to green.

**A8 — Direct session reopen — DONE** *(completed F8.2)*

Implemented 2026-09-20. New route `/results/:sessionId`; `Results` fetches the stored
session on mount when context does not already hold it, with a loading state, a distinct
**Session Not Found** state (HTTP 404, via `SessionNotFoundError`) and a separate **Could
Not Load Session** state for an unreachable backend. A fresh *live* analysis redirects
(replace) to `/results/<id>` so a reload works; demo results keep `/results`.
**Known gap:** the response does not carry the input images, so a reopened session shows
answer, evidence, confidence and trace but no source imagery (the boxes have nothing to sit
on). Fixing it needs an `inputImages` field on `AnalyzeResponse` and a second migration.
Original description:

Support navigating straight to a session URL by fetching it on mount when router state is
absent, with a distinct "session not found" state rather than a blank page.

---

#### Track B — The ML programme

Unblocked: **D1** and **D2** were closed 2026-09-20. Ordered by dependency; B5/B6/B7 are independent of each other
and can run in parallel given enough GPUs.

> **What BigEarthNet.txt actually contains, checked against the parquet and extracted files on
> 2026-09-20.** 464,044 co-registered S1/S2 pairs and 9,553,962 annotation rows; the `bench` split is
> 1,082 pairs and 15,029 rows (970 captions, 6,927 binary, 5,550 multiple-choice, 1,582 box rows). Each
> patch is 120x120 pixels at 10 m (a 1.2 km scene); S2 is `uint16` in three band resolutions, S1 is
> `float32` VV/VH. The annotations are about **land-cover classes** (presence, area, count, adjacency,
> season, climate, and boxes for LULC regions such as "largest patch of coniferous forest"), not about
> objects. So it can train caption, VQA, region grounding and optical+SAR fusion at Sentinel scale, but it
> cannot teach the model to find the vessels and tanks the demos show at 0.65 m, and it has no change
> pairs, so B7 still needs CDVQA or similar. This is the Sentinel-to-Cartosat domain gap (Appendix A) in
> concrete form. The box coordinate convention (normalised `[x0 y0, x1 y1]`) is inferred from one sample
> and must be confirmed before any adapter is trained on it.

| Step | Module | Work | Done when |
|---|---|---|---|
| **B1** | M0 | *(The `bench` split, 1,082 patches, is already extracted to `data/BigEarthNet/bench_subset/` by `tools/extract_bigearthnet_bench.py`; the training pool is not.)* Ingest BigEarthNet.txt via reBEN into LMDB/safetensors. Use the **official geographic split**, not a naive grid split, and log which tiles landed where. Apply the quality filter, dropping the bottom quartile, and log `pairs_in`/`pairs_kept` to a committed file. Acquire CMU-Data and SOMA-1M into a **separate** directory so they never mix with the single-image pool. | The filtered pool is reproducible from a committed script and the filter's effect is auditable. |
> **B1 status: thin slice DONE 2026-09-20** (`ml/b1_slice.py`, `ml/b1_slice_report.json`): 1,995 train and 206 validation patches, 17,955 + 1,854 examples, official split labels with a 2-cell spatial buffer. Full-scale B1 deliberately deferred until the recipe is proven. Two departures from the row below, both forced by the data: the official split is patch-level, not geographic (52 of 54 tiles appear in several splits), and the "drop the bottom quartile" quality filter is degenerate here (75% of patches score exactly zero), so an absolute cloud-like cap of 5% replaced it. Bounding-box rows were left out, since B6 grounding is trained separately.

| **B2** | M1 | Stand up serving on the pinned backbone. One parameterized `/infer` endpoint. **Adapter hot-swap with all LoRA deltas resident at once** — a hard requirement, since compound queries call two specialists per request and cannot tolerate a reload between them. Add `/health` and `/adapters`. Implement the task-token convention as one shared utility. | A synthetic two-adapter sequential call shows no latency spike on the second call. |
| **B3** | M2 | Query interpreter via few-shot prompting first, not fine-tuning (Appendix A #17). Constrain decoding to the `TaskSpec` JSON Schema so an out-of-enum `taskType` is structurally impossible. Build the exemplar set from the Problem Statement's own representative queries plus hand-written ambiguous cases. | Held-out accuracy meets the bar the team sets (Appendix A #18 — no target exists yet). |
| **B4** | M9 | Modality heuristic: band count, wavelength tags, pixel-distribution statistics into logistic regression or a shallow tree. **Deliberately not a neural network.** Sub-100 ms, CPU-only. | Wired into A1's ambiguous-modality fallback. |
| **B5** | M3 | VQA + captioning adapter. Frozen encoder and decoder, modality-specific projections for S1/S2, LoRA rank 8–16 on attention projections only. **Resolve Appendix A #12 here** — whether this adapter emits a structured LULC side-channel for fusion, or fusion parses its free text. Fusion cannot be built until this is decided. | VRSBench and RSVQA evaluated on held-out data, with the delta ablation run. |
> **B5 status update (2026-09-21):** two adapters were trained locally on the RTX 3050. Run 1 (old slice) showed no evidence of reading imagery; run 2 (leak-neutral `data/b1_v2`) passes the pre-registered test on `bench_hard` main but not for binary questions on held-out tiles (see `docs/PROGRESS_LOG.md`). It has still not run on Kaggle. Earlier note (2026-09-20): written, NOT yet run on Kaggle. `ml/b5_common.py`, `ml/b5_train_lora.py`, `ml/b5_eval.py`, `ml/b5_kaggle.ipynb`. The training loop ran locally for a few steps only. S2-only input; the S1/S2 modality-specific projections and the VRSBench/RSVQA evaluation named below are not done, and evaluation uses the BigEarthNet.txt `bench` sample instead.
| **B6** | M4 | Grounding adapter, **separately tuned** — never joint-trained with VQA/captioning, per the documented multi-task collapse. Boxes as tokenized sequences, not a detection head. Multi-candidate output mandatory. | Acc@0.5 reported honestly; grounding results always paired with a confidence badge in any demo material. |
| **B7** | M5 | Change-VQA adapter. CDVQA ingestion keeping `test2` as the honest reporting split. Siamese T1/T2 encoding with **difference-attention, not naive subtraction**, optimized jointly with the decoder. The deterministic count must be computed from the attention map, **independently of the text answer** — that independence is what makes the downstream cross-check non-circular. | Per-question-category accuracy reported, not averaged away. |
| **B8** | M6 | Domain-gap pipeline: GSD-normalization tiling and radiometric jitter toward Cartosat-2S, speckle injection matching RISAT, from public sensor specifications. Applied to a held-out slice as a stress-test ablation only — **never mixed into headline numbers**. Exposed as one always-on inference-time function. | A before/after ablation table exists for each adapter. |
| **B9** | M7 | Complementarity detector: SAR-DINO / RGB-DINO pair trained with InfoNCE. **The highest-risk deliverable in the system.** Communicate a go/no-go early so C3's rule-based fallback is flipped deliberately, with time to verify it — not discovered broken during demo prep. | Either trained and serving, or the fallback is verified end-to-end and **labelled as rule-based** in the demo and write-up. |
| **B10** | M8 | Fusion composition: implement whichever structured-extraction format B5 decided; design the verbalizer template so every claim is attributed to the supplying modality; build a small internal eval set and label it non-standard. | The verbalizer provably never receives raw pixels. |
| **B11** | M10 | Evaluation harness. The **fine-tuning delta ablation** — un-adapted backbone vs. trained adapter — as a committed, re-runnable script. This is the single most judge-legible proof that the mandatory adaptation requirement is met. Persist every run's output. | Every number in the write-up traces to a committed run. |
| **B12** | M11 | *Stretch only.* Decoupled perception/reasoning confidence tokens, calibrated on a validation slice, never the test split. **Do not start until B1–B11 and Track A are demo-ready.** | Rule 4 in the confidence chain moves from fallback-only to functioning. |

---

#### Track C — Integration

Needs A4 and the corresponding Track B modules. This is where the dummy specialists are
actually replaced.

**C0 — Remove the scenario-engine leaks.** Do this *first*, before any swap.
`ConfidenceScorer`, `ComplementarityDetector` and `MultimodalVerbalizer` all call
`scenario_engine.get_dynamic_result()` directly, not only the specialist adapters. If
those call sites survive, the scorer will keep overriding real model confidence with
canned rationales and the swap will appear to work while silently doing nothing.

**C1 — Query interpreter wiring** *(B5, needs Track B3)*. Call the model, validate against
`TaskSpec`, retry once with a repair prompt on validation error, raise a typed error on
the second failure. Ambiguous status returns without proceeding to the validator or
router. **Resolve Appendix A #5** — where `interpretation_failed` sits in the error
taxonomy; the recommendation is a rejection reason code, for consistency with the
frontend's existing rejection path.

**C2 — Specialist invocation layer** *(B8, needs Track B2/B5/B6/B7)*. Replace in-process
dummy calls with HTTP wrappers carrying per-call timeouts aligned to the latency budget.
Preserve multi-box and quantity fields untouched. Execute dependent compound plans in
strict sequence. Distinguish "specialist errored" (partial results, confidence forced to
Low) from "model serving is unreachable" (a 503) — they need different HTTP responses.

**C3 — Fusion orchestration** *(B9, needs Track B9/B10)*. Add the
`trained` / `rule_based` config switch **at a single call site**, not scattered through
the pipeline. Wire the domain-gap preprocessing hook — and **resolve Appendix A #13**
first: whether it applies to fusion only or to every specialist call. The SPDD implies
uniform, which would place it in C2's common entry point instead.

**C4 — Registry wiring** *(B15)*. Import the precondition table directly from the
validator rather than keeping the current hand-written copy, so the two cannot drift.
Source adapter versions from one authoritative place.

**C5 — Close the remaining contract gaps.** Appendix A #2 (`clarifyingQuestion` round
trip), #9 (which component tags query weak points — recommendation: the interpreter, as
it already holds the query and task type), #10 (lock Rule 3 vs. Rule 4 evaluation order
with an explicit test), #8 (the cross-tool agreement algorithm, still undefined).

---

#### Track D — Deployment

**Status (2026-09-20): implemented for the system that exists, unverified as images.** The plan below
assumes a gateway, a model server, a database and an object store. Only a FastAPI app, a static
frontend and SQLite exist, so D1 is two containers and a volume, and D3 gates the frontend on the
backend's healthcheck (200 only when the database opens). Not applicable yet: model-serving
readiness and a GPU attachment. Verified without Docker: the backend started with the container's
exact command and environment, its healthcheck script, an analyze cycle, a restart that kept the
session, and three concurrent real-HTTP requests. Not verified: the image builds, `compose up`, and
the CI workflow. A font CDN in the frontend broke the offline rule and was replaced by bundled fonts.

**D1 — Containers** *(B17.1)*. Real build contexts for frontend, api_gateway, model
serving (GPU-attached, adapters mounted as a volume), database and object store.

**D2 — Config wiring** *(B17.2)*. Mount config into every container; audit that no
service hardcodes what A4 externalized.

**D3 — Startup sequencing** *(B17.3)*. Model serving loads backbone, adapters and
detector before signalling readiness. The gateway waits on that health check via
`depends_on: condition: service_healthy` plus a Dockerfile `HEALTHCHECK` — **container
start order alone is not sufficient**. Migrations run idempotently from an entrypoint
script, not as a manual pre-deploy step.

**D4 — Smoke test** *(B17.4)*. From a clean checkout, confirm a full analyze cycle
triggers **no outbound network calls**, per the offline NFR. Then run the manual
demo-readiness checklist. **Load-test three concurrent requests** — Appendix A #23 notes
this target has never been tested.

---

#### Suggested order if one person is doing this

1. ~~**A2**~~ and ~~**A5**~~ — both done 2026-09-20. They closed the last Phase 7 gap
   and the worst demo hazard respectively.
2. ~~**A7**~~ — done 2026-09-20, brought forward after a render crash slipped past every
   Python test.
3. ~~**A4**~~ and ~~**A1**~~ — done 2026-09-20. Config is externalized, and the validator's
   CRS, overlap and ordering rules now fire on real rasters.
4. ~~**A3**~~ — done 2026-09-20 (SQLite via `sqlite3`); sessions are now queryable.
4. Close **D1** and **D2** (the decisions) in parallel with the above; they need nobody's
   keyboard, only an answer.
5. **B1 → B2 → B3**, then **B4**. At this point the interpreter is real and **C1** can
   land, which is a visible milestone on its own.
6. **B5 → B6 → B7**, then **C0** and **C2**. This is the real swap.
7. **B8**, **B9**, **B10**, **C3** — fusion last, because it carries the highest risk and
   has a working fallback.
8. **A6** and **A8** whenever there is slack; none of them blocks anything.
9. **B11** before any write-up. **Track D** before any deploy. **B12** only if everything
   else is done.

---

## 11. Technology Stack

| Layer | Planned | Actual |
|---|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS or equivalent, Leaflet | React 19, TypeScript, Vite, **plain CSS with custom properties**, oxlint. No Leaflet. |
| Backend | Python, FastAPI, Pydantic | As planned (FastAPI 0.116, Pydantic 2.12) |
| Raster handling | Rasterio / GDAL, Pillow, NumPy | Pillow; rasterio optional behind a try/except |
| AI / model layer | PyTorch, Hugging Face Transformers, PEFT / LoRA | Not present — deterministic scenario engine |
| Storage | Prototype: local files + SQLite. Future: PostgreSQL, MinIO | Local files for images, overlays and reports; SQLite (stdlib `sqlite3`) for session records. No PostgreSQL or MinIO. |
| Reports | HTML template, PDF renderer, JSON export | HTML template + JSON + PDF via `xhtml2pdf` |
| Deployment | Docker, Docker Compose | Two containers (FastAPI backend, nginx-served frontend) plus a named volume, via `docker-compose.yml`; both images build and run in CI |

The first prototype should remain lightweight and hackathon-focused.

---

## 12. Repository Structure

Actual layout — imports are absolute from the repository root, so the backend must be run
from the root:

```text
SatQuery/
├── backend/
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── api/            routes_analyze, routes_session, routes_system
│       ├── orchestrator/   the 8 pipeline stages
│       ├── specialists/    base, vqa_caption, grounding, change_vqa, scenario_engine
│       ├── fusion_pipeline/ complementarity_detector, verbalizer
│       ├── schemas/        the SPDD §8 contracts
│       └── services/       metadata, overlay, report, storage
├── frontend/
│   └── src/
│       ├── pages/          Home, UploadQuery, Results
│       ├── components/     14 components
│       ├── context/        SatQueryContext
│       ├── data/           mockScenarios
│       ├── services/       api.ts
│       └── types/          satquery.ts
├── tests/                  pytest suite (TestClient, no server needed)
├── docs/
├── requirements.txt
└── pytest.ini
```

Backend storage is written at runtime to `backend/storage/sessions/<sessionId>/` with
`inputs/`, `evidence/` and the rendered reports; session records live in the SQLite
database (`backend/storage/satquery.db`, or `SATQUERY_DATABASE_PATH`). It is gitignored.

---

## 13. Testing Strategy

Every phase must have tests appropriate to that phase.

**Unit tests** — query task mapping, validation rules, routing, evidence schema,
confidence logic, trace generation, report generation.

**Integration tests** — `Upload → Analyze → Result` for every supported task.

**Demo tests** — before any presentation, verify malformed input rejection, ambiguous
grounding, quantity discrepancy producing Low confidence, the compound workflow trace,
report parity, and a clean startup.

Current suite: 106 pytest tests (plus 55 Vitest tests) using FastAPI's `TestClient`, writing to a temporary
storage root so runs never pollute `backend/storage/`. Run with `python -m pytest` from
the repository root; no server needs to be running.

---

## 14. Definition of Done

The prototype is ready when a fresh user can:

1. Open SatQuery AI.
2. Upload one or two images.
3. Enter a natural-language query.
4. Submit the request.
5. Watch the observable agent workflow.
6. See task and validation results.
7. See a relevant dummy specialist execute.
8. See visual evidence.
9. See confidence and rationale.
10. Open the execution trace.
11. Download a PDF report.
12. Try an invalid request and receive a polished rejection.

**No manual edits to backend data should be required during the live demo.**

All twelve hold today.

---

## 15. Future Real-Model Integration

After the dummy system is stable, integrate real models **one specialist at a time**:

```text
1. Real VQA / Caption
2. Real Grounding
3. Real Change-VQA
4. Real Evidence / Change overlays
5. Real Optical-SAR complementarity detector
6. Real fusion verbalization
```

Keep the orchestrator, API contracts, evidence model, verification layer and UI unchanged
wherever possible.

The source documents specify BigEarthNet.txt for remote-sensing adaptation, VRSBench for
captioning/grounding/VQA evaluation, RSVQA for single-image VQA cross-check, CDVQA for
multitemporal change VQA, a shared frozen visual + language backbone, and task-specific
LoRA adaptation. The SPDD further defines task-specific adapters and a Change-Enhancing
Module. **Real-model integration must follow those contracts rather than replacing the
architecture with an unrelated end-to-end model.**

> **Note for whoever does this work.** `ConfidenceScorer` and both fusion modules
> currently call the scenario engine directly, not only the specialist adapters. Those
> call sites must be removed at the same time, or the scorer will keep overriding real
> model confidence with canned rationales.

### 15.1 Domain-gap awareness

Keep the Sentinel → Cartosat/RISAT gap visible in the architecture. Preprocessing hooks
must support GSD normalization, radiometric/histogram adaptation, SAR speckle-noise
characteristics and cross-sensor robustness testing.

**Do not claim that dummy-model performance proves domain robustness.**

---

## 16. Scope Guardrails

Do not let the project expand into unnecessary infrastructure during the prototype phase.
Explicitly deferred:

- Kubernetes autoscaling
- Production-grade MLOps
- Triton / TensorRT optimization
- Vector database / historical recall
- QGIS plugin
- End-to-end generative optical-SAR fusion trained from scratch

The goal is a strong, complete, demonstrable MVP.

---

## 17. Execution Rules

1. Work one phase at a time.
2. Do not start the next phase automatically.
3. Treat the source `.md` documents as source-of-truth references.
4. Preserve documented API contracts.
5. Preserve task names and routing semantics.
6. Keep dummy models isolated from orchestration.
7. Keep the frontend model-agnostic.
8. Do not expose hidden chain-of-thought.
9. Only expose observable execution steps.
10. Prefer simple, testable implementations.
11. Do not add speculative enterprise infrastructure.
12. After each phase: run the application, run the tests, fix errors, summarize files
    changed, summarize what works, summarize remaining work, then stop and wait.

---

## 18. Final Product Definition

The prototype communicates one idea:

> **SatQuery AI transforms a natural-language question and satellite imagery into a
> verified, evidence-grounded and auditable answer.**

It succeeds when a judge can visually see:

```text
ASK → UNDERSTAND → VALIDATE → ROUTE → ANALYZE → VERIFY → EXPLAIN
```

without needing to understand the internal ML implementation to appreciate the agentic
system.

---

## Appendix A — Flagged Ambiguities & Gaps

Every place the source documents conflict, are silent, or leave a choice unresolved.
Resolved entries record what the code actually decided; open entries still need a team
decision.

| # | Ambiguity | Module | State |
|---|---|---|---|
| 1 | Leaflet vs. deck.gl for the map layer | F0.1 | **Open** — no map implemented |
| 2 | `clarifyingQuestion` exists on `TaskSpec` but the SPDD's literal `AnalyzeResponse` never exposes it | B1.2, F6.3 | **Open** — the field is on `TaskSpec` and reaches the client inside `taskSpec`, but no dedicated round-trip UX exists |
| 3 | `AnalyzeResponse` lacks the georeference/CRS info the frontend needs to choose map vs. plain image | F7.1 | **Open** |
| 4 | Python version and exact library versions unpinned | B0.2 | **Resolved** — Python 3.12, floors pinned in `requirements.txt` |
| 5 | `interpretation_failed` fits neither the §14.1 rejection table nor §14.2's runtime failures | B5.2 | **Open** — recommendation stands: add it as a rejection reason code for contract consistency |
| 6 | Object store: local filesystem vs. S3/MinIO | B3.1 | **Resolved** — local filesystem |
| 7 | How `cloudMaskPercent` is actually computed | B6.1 | **Resolved** — 8-bit brightness approximation, unknown otherwise; not a cloud-detection model |
| 8 | Cross-tool agreement algorithm and threshold described narratively, no formula given | B10.2 | **Open** |
| 9 | SPDD §7.2 Rule 3 assumes query-weak-point tagging exists but assigns no component to set it | B11.1 | **Open** — recommendation: the Query Interpreter sets it, since it already holds the query and task type |
| 10 | Rule 3 vs. Rule 4 evaluation order (look-ahead discount vs. post-hoc) | B11.3 | **Open** — SPDD phrasing implies look-ahead; needs a test to lock the semantics |
| 11 | Server-side overlay rendering is assumed but assigned to no component | B13.3 | **Resolved** — `services/overlay_service.py` |
| 12 | `vqa_caption_specialist`'s documented output has no LULC-class structure that fusion sub-step 1 requires | M3.1, M8.1, B9.1 | **Open** — must be resolved jointly before fusion integration |
| 13 | Domain-gap normalization hook: fusion-only or all specialists | B9.4, M6.4.1 | **Open** — SPDD §6 implies uniform |
| 14 | Frontend test tooling and coverage target unspecified | F9 | **Resolved** — Vitest + React Testing Library; no coverage target set |
| 15 | Backend unit-test coverage target unspecified | B16.1 | **Open** — 106 tests, no percentage target agreed |
| 16 | Backbone model choice given only as examples, never pinned | M1.1 | **Open** — blocks M2–M5 training |
| 17 | Query interpreter: fine-tuned or prompted-only | M2.1 | **Open** — recommendation: start prompted-only |
| 18 | No accuracy target for the query interpreter | M2.4 | **Open** |
| 19 | Domain-shift proxy data availability genuinely uncertain | M0.5 | **Open risk** |
| 20 | Compute budget (GPU-days, hardware) unconfirmed | M0.1, M3.3 | **Open risk** |
| 21 | Modality heuristic serving location: CPU-inline or separate service | M9.3 | **Open** |
| 22 | Complementarity detector readiness — the highest-risk deliverable | M7.4 | **Open risk** — rule-based fallback is what ships today |
| 23 | Concurrency target (3 simultaneous requests) stated but untested | B17.4 | **Exercised, not benchmarked** — 3 concurrent requests succeed with distinct sessions (`tests/test_deployment.py`, and over real HTTP against uvicorn: 0.16 s wall on dummy specialists). No latency target exists to measure against, and real inference will change this |
| 24 | Auth/session model intentionally minimal; full RBAC deferred | — | **Accepted** — noted so no module over-builds it |

---

## Appendix B — Reconciliation of the Two Source Plans

Where the Hackathon Development Plan and the Implementation Plan disagreed, and what this
document adopts.

| Topic | Implementation Plan said | Development Plan said | Adopted |
|---|---|---|---|
| Repository layout | Monorepo with `services/api_gateway`, `services/orchestrator`, … as separate deployable services | `backend/api_gateway`, `backend/orchestrator`, … | **What exists**: a single `backend/app/` package. The microservice split was never built and is not needed at prototype scale. |
| Python dependencies | Per-service `services/requirements.txt` plus extras | Not specified | One `requirements.txt` at the repository root. |
| Styling | Not specified | Tailwind CSS or equivalent | Plain CSS with custom properties. No Tailwind. |
| Map layer | Leaflet, assumed for concreteness | Leaflet or equivalent | Deferred — no map implemented (F7 is TODO). |
| Processing view | Not specified | Optional `/processing` route or a modal state | A full-screen state on `/analyze`. |
| Persistence | PostgreSQL/SQLite via SQLAlchemy + Alembic migrations | SQLite for the prototype | SQLite via stdlib `sqlite3` (`session_repository.py`). B4 DONE; Postgres/Alembic not used. |
| API base URL | `VITE_API_BASE_URL` environment variable | Not specified | `API_BASE` in `services/api.ts`, read from `VITE_API_BASE_URL` (default `http://127.0.0.1:8000`). Done in A4/A5. |
| Deployment | Docker Compose with health-gated startup, plus CI | Docker, Docker Compose | Built and green in CI (Track D, 2026-09-20). Single backend service, so no model-serving health gate yet. |
| Dummy model file | Not addressed | `specialists/dummy_scenarios.py` | `specialists/scenario_engine.py`. |
| Test layout | `tests/unit/` and `tests/integration/` | Same | A flat `tests/` package split by subject, using `TestClient` — which removes the need for a running server and therefore the unit/integration directory split. |
| Confidence default | Five-rule SPDD list including the stretch-goal Rule 4 | Simplified four-branch MVP defaulting to Medium | The MVP chain, with scenario-calibrated High/Medium where the scenario engine supplies a rationale. |
| `ValidationMessage.tsx` | Not mentioned | Listed in the repository structure | Removed — it was never imported by any component. |

**The essential difference between the two documents was granularity, not content.** The
Development Plan described the product and the phase order; the Implementation Plan
described the tasks and their dependencies. Both layers are preserved here: sections 1–9
are the product and roadmap, section 10 is the task breakdown.
