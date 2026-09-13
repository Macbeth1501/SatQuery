# SatQuery AI — Solution Proposal (SIH26167)
### An Agentic Vision-Language Assistant for Multimodal Remote Sensing Image Analysis

---

## 1. Problem Understanding & Reframing

Strip away the buzzwords and SIH26167 is asking for three things bolted together, and the third one is the actual point:

1. **A remote-sensing-adapted perception layer** — models that actually understand Sentinel/Cartosat/RISAT imagery, not a generic VLM squinting at a satellite photo the way it would squint at a photo of a cat.
2. **Task coverage across three input regimes** — single image, cross-modal (optical+SAR) pair, bi-temporal pair — each with genuinely different failure modes.
3. **An agentic controller that behaves like a careful analyst, not a chatbot** — it must interpret intent, *validate that the requested analysis is even physically possible on the given input*, choose tools, execute them in the right order, and produce an answer that can be audited line by line.

The literature survey (and our own reading of the PS) makes clear that (1) and (2) are largely **solved-adjacent problems** — there is a well-validated recipe (frozen vision encoder + LoRA-adapted LLM decoder) that gets a small model from unusable to competitive on BigEarthNet.txt-style tasks. The genuinely hard, under-solved part is (3), and specifically three sub-problems inside it that most teams will underestimate:

- **The domain-gap problem.** BigEarthNet.txt is built on Sentinel-1 (SAR, ~10 m) and Sentinel-2 (multispectral, 10–60 m). ISRO's own evaluation set uses **Cartosat-2S** (pan 0.65 m, multispectral 2 m — a 5–30× resolution jump) and **RISAT** SAR (stripmap ~3 m, different band/incidence-angle characteristics from Sentinel-1's C-band IW mode). A model fine-tuned only on Sentinel statistics and never explicitly hardened against this shift will look great on the leaderboard-adjacent BigEarthNet split and then degrade on the exact ISRO/SAC set that decides the final score. This is a physics/sensor problem, not a modeling nuance, and it's the single biggest technical risk in this PS.
- **The "combine outputs" problem for optical–SAR fusion.** The PS explicitly says the agent should "combine the generated outputs," and the survey confirms there is **no existing generative, natural-language optical–SAR fusion model** — every precedent either fuses pixels for closed-set classification/segmentation, or doesn't fuse modalities at all. Naively concatenating SAR and optical channels into one VLM has been shown to *hurt* accuracy (see §2, EarthDial-S2 / RS-InternVL ablations) rather than help. This has to be solved with genuine cross-modal alignment, not more channels.
- **The "tool orchestration is not generic function-calling" problem.** A recent survey of agentic AI in remote sensing explicitly warns that general-purpose tool-orchestration frameworks treat tools as interchangeable interfaces and focus on when and in what order to invoke them, an abstraction that obscures the semantics and persistent effects of geospatial transformations because geospatial tools are stateful, order-dependent, and computationally intensive. A satellite image has a CRS, a footprint, a GSD, a modality, an acquisition date, and possibly a nodata mask — running a "captioning" tool on a SAR image, or a "change-VQA" tool on two images with no temporal or spatial overlap, is not a wrong answer, it's an invalid operation. Most hackathon teams will build a ReAct-style LLM router that treats every specialist model as a black-box function; a system that *type-checks* its own inputs before calling a specialist is qualitatively more defensible to a judging panel evaluating "Input Validation" and "Execution Trace" as explicit line items.

**Reframe:** SatQuery AI is not "a chatbot for satellite images." It is a **geospatial compiler** — it parses a natural-language query into a typed task specification, checks that specification against the physical properties of the supplied imagery, and only then dispatches to specialist models, verifying their outputs before presenting them. Treating it this way — rather than as prompt-engineering-plus-API-calls — is what will separate a working demo from a system a judge believes could plausibly sit in front of real Cartosat/RISAT data.

---

## 2. Related Work Summary

### 2.1 What the literature survey already establishes (synthesized, not repeated in full)

- **Fine-tuning is non-negotiable and cheap.** Across five independently developed systems (RS-InternVL, GeoChat, RS-LLaVA, EarthDial, the Qwen/CDVQA study), the same recipe recurs: freeze the vision encoder, freeze the base LLM, train only lightweight modality-projection layers plus LoRA adapters on the LLM's attention projections. This yields **30+ point accuracy swings** over both larger generalist VLMs and un-tuned RS-VLMs (e.g., RS-InternVL: binary VQA 61.96 → 73.29, captioning BLEU-4 0.96 → 34.04) at a cost of ~5.8M trainable parameters out of 1.1B, trainable in ~2 GPU-days.
- **No single existing model covers the full PS mandate.** GeoChat lacks temporal/SAR; RS-LLaVA lacks grounding and fusion; CDVQA/Qwen-change-VQA models are optical-only; EarthDial covers multi-sensor+temporal conversation but not explicit fusion reasoning; MM-OVSeg fuses optical-SAR but only for pixel-wise segmentation, not language. This is the direct empirical case for an agentic, multi-specialist system rather than one monolithic model — which is exactly what the PS asks for.
- **Naive multi-sensor input does not help.** Feeding SAR/multispectral channels into an RGB-pretrained backbone without dedicated training can *reduce* accuracy (EarthDial-S2 MCQ accuracy collapses to 8.43% vs. 32.94% for the RGB variant of the same model). Real fusion requires an explicit alignment mechanism (MM-OVSeg's Cross-Modal Unification module), not concatenation.
- **Counting/magnitude reasoning is the universal weak point.** RS-LLaVA struggles with counting; the Qwen change-VQA study's hardest categories (smallest-change, change-ratio) sit at 30–60% accuracy vs. 80–85% for binary/directional change questions. This is a recurring, cross-paper signal that should shape confidence estimation, not just accuracy targets.

### 2.2 What we found beyond the survey (2025–2026 agentic-AI-in-RS literature)

The survey stops at task-level model comparisons and does not deeply cover the *orchestration layer itself* — which is the PS's actual novelty ask. Three recent works fill this gap and directly shape our design:

- **RS-Agent** (Xu et al., 2024) is the closest existing precedent to "SatQuery AI": a domain-adapted agent connecting user intent to remote-sensing workflows through structured task planning and tool orchestration, with a Central Controller, a dynamic toolkit, a Solution Space for expert guidance, and a knowledge space, and it reports over 95% task-planning accuracy across 9 datasets and 18 tasks, including native support for optical and SAR imagery with automatic organization of SAR-specific processing tools into executable workflows. This validates the four-component decomposition (controller / toolkit / expert guidance / knowledge retrieval) we adopt below, but RS-Agent is evaluated on classification/counting/VQA — not on bi-temporal change or generative optical-SAR fusion, which remain open.
- **ThinkGeo** (Shabbir et al., 2025) is a benchmark, not a system, but it is diagnostically important: it evaluates LLM agents with a ReAct-style loop over 14 executable RS tools across 486 tasks, and its own tool-usage analysis shows Calculator, text-to-bounding-box, and region-attribute-description are the most frequently invoked tools, reflecting an emphasis on spatial computation, object localization, and attribute reasoning — i.e., real RS queries decompose into small, composable, spatially-grounded sub-operations rather than one giant end-to-end inference call. This supports designing SatQuery AI's toolkit as fine-grained, composable operations rather than one opaque "answer the query" specialist per task type.
- **"Agentic AI for Remote Sensing: Technical Challenges and Research Directions"** (2026) is the most important find of this search: it is a direct critique of applying generic agent frameworks to Earth observation, arguing that tool orchestration is a central challenge because geospatial tools are stateful, order-dependent, and often computationally intensive, unlike the abstract, interchangeable tools assumed by general-purpose orchestration frameworks such as ToolOrchestra, OctoTools, and VerlTool, and that current agents inherit visual priors from natural-image pretraining that implicitly assume consistent object scales and stable appearance statistics, priors which break down given how visual appearance varies across sensors, resolutions, viewing geometries, and environmental conditions in remote sensing. This paper is essentially describing, in academic language, the exact domain-gap and naive-orchestration failure modes we identified independently in §1 — it is strong external validation that these are the right problems to solve, not over-engineering.
- **The broader "Agentic AI in Remote Sensing" WACV 2026 survey** confirms the field is moving from "static VLM answers a question" toward trajectory-aware evaluation that assesses planning and reasoning correctness across multi-step processes, rather than just final output accuracy — which matches SIH26167's own emphasis on execution trace and auditability as scored line items, not window dressing.

### 2.3 Gaps this proposal must close independently

1. No public system combines *typed, contract-checked orchestration* (rather than free-form ReAct tool-calling) with remote-sensing specialists — this is the orchestration-layer novelty space SatQuery AI should occupy.
2. No public system addresses the **Sentinel→Cartosat/RISAT domain-shift** problem explicitly; it is not mentioned in RS-Agent, ThinkGeo, or the base survey's ten papers, because none of them target ISRO-specific sensors.
3. Generative (language-producing) optical-SAR fusion remains unsolved in the literature (survey §14); we must design around this gap rather than pretend it's solved.

---

## 3. Proposed Solution Overview

**SatQuery AI = a typed task-graph agent (not a ReAct chatbot) sitting on top of one multi-task, remote-sensing-adapted vision-language specialist, one change-reasoning specialist, and a structured optical-SAR fusion pipeline — all wrapped in an explicit input-validation and execution-audit layer.**

Concretely:

- **One shared, multi-task vision-language backbone** (RS-InternVL-style: frozen ViT + LoRA-adapted small LLM) handles single-image VQA, captioning, and grounding from one fine-tuning run on BigEarthNet.txt, because the survey shows this multi-task recipe already works well in a single model — building three separate models here would be effort spent on redundancy, not capability.
- **A second, separately LoRA-adapted instance of the same family** handles bi-temporal Change-VQA / change description, fine-tuned on CDVQA, because change reasoning needs different attention patterns (cross-image differencing) than single-image reasoning and the survey shows dedicated change-tuning meaningfully outperforms treating it as "VQA over two images."
- **Optical-SAR fusion is solved as a two-step structured pipeline, not a single generative fusion model** (justified in §5.4) — this is a deliberate deviation from the "obvious" approach and directly addresses the literature gap in §2.3.
- **The orchestrator is a typed task graph (LangGraph-style state machine) with an explicit Compatibility Validator node**, not a free-form agent loop — this is the other deliberate deviation, and it's what makes "Input Validation," "Agentic Orchestration," and "Execution Trace" — three separate scored evaluation rows in the PS — fall out of the architecture almost for free instead of being bolted on as an afterthought.
- **A domain-shift mitigation layer** (resolution-normalization tiling + radiometric-jitter augmentation + a lightweight test-time calibration hook) sits between input validation and specialist dispatch, specifically to survive the Sentinel→Cartosat/RISAT gap.

---

## 4. USP / Innovation

**What the "obvious first-pass AI solution" looks like (and why we are not building it):**

Almost every team given this PS and an LLM to help them draft a proposal will converge on: *"Fine-tune GeoChat/LLaVA on BigEarthNet, wrap it in a LangChain agent with function-calling over 5–6 tools, feed both SAR and optical channels into the same VLM for fusion, use GPT-4o or a cloud API as the orchestrator brain, and show a Streamlit demo."* This is not a bad idea — it is the modal idea, and a panel that reviews 30+ submissions on the same PS will see it 20 times.

**Where SatQuery AI deviates, and why each deviation is substantive rather than cosmetic:**

| Obvious approach | Our deviation | Why it's a real improvement, not novelty theater |
|---|---|---|
| ReAct/function-calling agent treats every specialist as an interchangeable black box | **Typed task graph with a pre-execution Compatibility Validator node** that checks modality, CRS, GSD, footprint overlap, and temporal validity *before* any specialist runs | Directly answers the PS's mandatory step 2 ("Validate the input... image compatibility") as a structural property of the system, not a prompt instruction the LLM might forget. Also grounded in a 2026 critique paper showing generic orchestration frameworks fail exactly here. |
| Concatenate SAR + optical channels into one VLM and hope fusion emerges | **Structured two-stage fusion**: run the single-image specialist independently on each modality to get structured semantic evidence (LULC presence/area per class), then a lightweight complementarity detector flags where the two modalities agree/disagree/complement, and only then is it verbalized | The survey shows naive channel concatenation *actively hurts* accuracy (EarthDial-S2 case) and no generative fusion model exists to copy. This is the technically honest response to a real, cited gap — not the AI-generated boilerplate answer of "we'll build a fusion transformer." |
| Assume BigEarthNet.txt (Sentinel) fine-tuning transfers to the ISRO/SAC evaluation set | **Explicit domain-gap engineering**: GSD-normalization tiling, radiometric augmentation spanning Sentinel-to-Cartosat dynamic range, and a small held-out calibration protocol | Cartosat-2S is 5–30× higher resolution than Sentinel-2, and RISAT SAR differs from Sentinel-1 in band/incidence geometry. Nobody in the survey addresses this because none of the ten papers target ISRO sensors. This is the single deviation most likely to separate a demo that "works on BigEarthNet" from one that survives the actual judging dataset — and it costs almost nothing to implement (it's an augmentation and calibration policy, not a new model). |
| Route through a hosted LLM API (GPT-4o, Claude, Gemini) as the "brain" | **Fully open-weight, self-hostable stack** (small instruct LLM as controller + LoRA-adapted open VLMs as specialists), with cloud APIs as an optional non-sensitive demo path only | ISRO/SAC imagery (Cartosat/RISAT) is government-sensitive geospatial data; a system whose default path ships imagery to a third-party API is a governance red flag for this specific customer, not a neutral engineering choice. An architecture that runs entirely offline/on-prem is a meaningful differentiator to a defense-adjacent evaluator, and almost no hackathon team will think to raise it. |
| Confidence = ask the LLM to output a percentage | **Evidence-based confidence score**: combines specialist token-level uncertainty, a task-type prior calibrated against the survey's own documented weak points (counting, magnitude, smallest-change), and cross-specialist agreement | Verbalized LLM confidence is well known to be poorly calibrated. Grounding the confidence score in *empirically documented* failure modes from the literature we reviewed is a defensible, judge-legible design decision rather than a black box. |

**What would make a judge say "this isn't what everyone else submitted":** the Compatibility Validator rejecting an invalid query live in the demo (e.g., asking for change detection on a SAR+optical pair from different dates and different footprints, and watching the system explain *why* it refuses and what it needs instead), and a visible, versioned answer to "what happens to your BigEarthNet-tuned model on Cartosat-resolution imagery" — because almost no other team will have an answer to that question at all.

---

## 5. Methodology

### 5.1 Candidate approaches considered and rejected

Before settling on the design in §3, we evaluated and rejected the following, to avoid pattern-matching to the first plausible architecture:

**A. Single end-to-end multimodal model for everything (one VLM handles VQA + captioning + grounding + change + fusion via one giant instruction-tuning run).**
Rejected: the survey shows dedicated change-reasoning and dedicated fusion-alignment both meaningfully outperform generalist multi-task tuning; also operationally risky in a hackathon timeframe — one failed fine-tuning run breaks the entire system with no fallback. A modular specialist design isolates failure and matches what the PS explicitly asks for ("may employ multiple specialised models").

**B. Naive ReAct / OpenAI-style function-calling agent (LangChain `AgentExecutor` with a flat toolset).**
Rejected as the *primary* orchestration mechanism — it is exactly the pattern critiqued in the 2026 agentic-RS paper for treating stateful, order-dependent geospatial operations as interchangeable functions, and it does not naturally produce the auditable, structured execution trace the PS requires as a scored deliverable. (We do keep ReAct-style *reasoning traces* as a user-facing explanation layer on top of the typed graph — see §7.)

**C. Full generative optical-SAR fusion VLM trained end-to-end with a dedicated cross-modal alignment module (MM-OVSeg-style Cross-Modal Unification, but for language output instead of segmentation).**
Rejected for the hackathon timeframe specifically (not rejected as a good idea — flagged as future work in §9): MM-OVSeg's own alignment training is a multi-day, multi-GPU undertaking on a purpose-built dataset; replicating it for a *generative* task with no existing training corpus is a research project, not a hackathon deliverable. The structured two-stage pipeline (§5.4) captures most of the practical value at a fraction of the engineering risk.

**D. Cloud-API-only orchestration (GPT-4o/Gemini as both controller and vision specialist via API, with light prompt engineering, no fine-tuning).**
Rejected outright — the PS explicitly disallows a generic unadapted LLM/VLM as the solution, and the survey's own ablations (VRSBench: GeoChat's BLEU-1 collapses from 46.7 to 13.9 without fine-tuning) show this approach would also simply perform badly, independent of the governance concerns raised in §4.

**Chosen approach:** the modular, typed-orchestration design in §3, because it is the only option that (a) satisfies every mandatory functional-scope item individually with a defensible, benchmarked recipe, (b) is buildable within a hackathon timeframe using proven LoRA-based fine-tuning, and (c) has a genuine, citable answer for the two hardest open problems in this PS (fusion, and orchestration-as-validation) rather than hand-waving past them.

### 5.2 Remote-sensing adaptation (mandatory requirement)

- **Backbone:** a compact open-weight VLM in the 1–4B parameter range (e.g., InternVL3-1B or a Qwen2.5-VL/Qwen3-VL small variant) — chosen over a 7B+ model because the survey's own RS-InternVL result shows a 1B model, properly fine-tuned, *beats* 7B+ generalist VLMs on every RS task category, and a smaller model is dramatically cheaper to fine-tune and to serve live during a demo.
- **Recipe:** freeze the vision encoder; add small modality-specific linear projections for S1 (SAR) and S2 (multispectral) tokens; apply LoRA (rank 8–16, α=32) only to the LLM's attention projection matrices. This is the single most cross-validated recipe in the entire literature survey (independently reproduced by five different research groups) and requires training <1% of total parameters.
- **Data:** BigEarthNet.txt (mandatory), using the dataset's own train/val split; the manually curated 1,082-pair benchmark split is reserved strictly for our own internal evaluation, never touched during training, to get an honest read on generalization before the ISRO/SAC set is applied.
- **Multi-task in one model:** captioning + binary/MCQ VQA + referring-expression grounding are trained jointly from BigEarthNet.txt's existing annotation taxonomy, because RS-InternVL demonstrates one model can absorb all three tasks well above baseline — this satisfies "Single-Image VQA" (mandatory) plus *both* optional single-image tasks (captioning **and** grounding) from one fine-tuning run, exceeding the PS's "at least one" requirement at negligible extra cost.

### 5.3 Bi-temporal change analysis

- **Change-VQA specialist:** a second LoRA adapter on the same model family, fine-tuned on CDVQA, following the benchmarked Qwen3.5-2B-class recipe (LoRA r=16 on Q/K/V/O projections, frozen vision tower) — chosen because it is documented to outperform dedicated prior architectures (CDVQA baseline, SOBA, VisTA) on both AA and OA while remaining compute-cheap.
- **Change description:** generated from the same adapter by prompting for free-form description rather than only categorical answers, reusing the same weights — avoids training a third model for a closely related task.
- **Optional spatial change map (stretch goal, matches PS's "may be generated where reference masks are available"):** a lightweight bi-temporal difference model (Siamese feature-difference + shallow segmentation head, in the spirit of standard change-detection architectures) trained/fine-tuned on a small labeled change-detection set (e.g., LEVIR-CD or xBD for the disaster-relevant framing). This is explicitly scoped as optional because reference masks are not guaranteed to be available on the ISRO/SAC set, and the PS itself flags this as conditional.
- **Confidence handling:** per the survey's own empirical finding, change-ratio and smallest-change questions are structurally harder (30–60% accuracy vs 80–85% for binary/directional). The confidence module (§6, stage 7) applies a lower prior specifically to these query subtypes, rather than reporting uniform confidence.

### 5.4 Optical-SAR cross-modal analysis — the structured fusion pipeline

This is the least-precedented mandatory requirement (survey §14), so we spell out the mechanism precisely:

1. Run the same fine-tuned single-image specialist (§5.2) **independently** on the optical image and the SAR image, extracting *structured* semantic evidence for each: LULC class presence, approximate area share, and any grounded regions — not free text yet.
2. A lightweight **complementarity detector** (a small rule-augmented classifier, trainable directly on BigEarthNet.txt's paired S1/S2 labels since both modalities already share ground-truth LULC references) compares the two structured evidence sets and tags each LULC region as: *agreement* (both modalities detect it), *optical-only* (e.g., a spectral signature SAR cannot resolve), or *SAR-only* (e.g., a water body or built-up structure obscured by cloud in the optical scene but visible in backscatter — the PS's own example query about built-up/water regions is exactly this case).
3. The controller LLM verbalizes this structured comparison into natural language ("the SAR image reveals a water body not visible in the optical scene, consistent with cloud cover over the north-east quadrant..."), citing which modality supplied which piece of evidence — this satisfies the PS's "combine the generated outputs" instruction literally and auditably, rather than asking one model to silently fuse pixels and hoping the explanation is faithful to what it actually did.

This deliberately avoids the failure mode documented in the survey (naive channel concatenation degrading accuracy) by never asking any single model to jointly ingest raw SAR and optical pixels — each modality is understood on its own terms first, and fusion happens at the semantic/structured level, which is both more robust and more explainable.

### 5.5 Agentic orchestration (the core novelty layer)

The controller is implemented as a **typed, directed graph of nodes** (state machine), not a flat function-calling loop:

1. **Query Interpreter** (text-only, small instruct LLM) — parses the natural-language query into a structured task spec: `{task_type, required_modalities, required_temporal_pairing, requested_parameters}`. Kept text-only and decoupled from the vision specialists deliberately: it is far cheaper to run, easy to prompt with the PS's own representative queries as few-shot exemplars, and can be swapped or upgraded without ever touching the fine-tuned vision models.
2. **Compatibility Validator** — checks the task spec against the actual uploaded image(s): file format (GeoTIFF/TIFF/PNG/JPEG), CRS and reprojection feasibility, modality tags, footprint overlap (for pairs), and — for bi-temporal pairs — acquisition-date ordering and spatial co-registration quality. If the spec is not satisfiable, the graph terminates here with a specific, human-readable reason rather than forcing a downstream model to guess.
3. **Specialist Router** — deterministic mapping from validated task spec to one or more specialist nodes (VQA/captioning/grounding specialist, change specialist, fusion pipeline) — no LLM "decides" this step by free-form reasoning; it is a lookup against a small, explicit, testable table, which is both faster and dramatically easier to audit than an LLM-decided route.
4. **Specialist Execution** — the chosen specialist(s) run; outputs are structured (not free text) wherever possible (bounding boxes, category labels, area estimates), and packaged into an internal "evidence ledger" object.
5. **Verifier node** — a lightweight consistency check (e.g., does a grounded bounding box actually fall inside the image bounds; does a "yes" VQA answer contradict a captioning statement) before anything is shown to the user; failures here downgrade the confidence score rather than silently passing through.
6. **Response Composer** — the controller LLM converts the evidence ledger into natural language, always citing which specialist/tool produced which claim.
7. **Confidence & Trace Emitter** — computes the evidence-based confidence score (§5.3) and serializes the full execution trace (selected task, models/tools invoked, parameters, per-step outputs, timing) as the mandatory auditable summary.

---

## 6. End-to-End Pipeline

| Stage | What happens | Tools / frameworks |
|---|---|---|
| **1. Ingestion** | User uploads 1–2 images (GeoTIFF/TIFF/PNG/JPEG) + a text query via the web UI | React frontend, chunked upload |
| **2. Metadata extraction** | Read CRS, resolution, band count, footprint, acquisition date (if present in tags); flag missing/ambiguous metadata | `rasterio`, `GDAL`, `pyproj` |
| **3. Query parsing** | Query Interpreter LLM converts text → structured task spec (JSON schema) | Small open-weight instruct LLM (e.g., Qwen2.5-7B-Instruct), served via `vLLM`/Ollama |
| **4. Compatibility validation** | Task spec checked against image metadata; reprojection triggered if CRS mismatch but resolvable; hard rejection with explanation if not | Custom validator (Python), `pyproj`/`shapely` for footprint IoU |
| **5. Domain-shift normalization** | Tile to a fixed GSD-normalized patch size; apply modality-specific radiometric normalization (Sentinel vs. Cartosat/RISAT statistics handled separately) | Custom preprocessing, informed by §8.2 |
| **6. Specialist dispatch** | Router sends normalized input + task spec to one or more of: VQA/captioning/grounding specialist, change-VQA specialist, fusion pipeline | LoRA-adapted VLM checkpoints served via `vLLM` or HF `transformers` |
| **7. Structured evidence collection** | Each specialist returns structured outputs (labels, boxes, scores) into the evidence ledger | Pydantic-typed internal schema |
| **8. Verification** | Cross-check evidence for internal consistency; flag contradictions | Rule-based verifier + lightweight NLI check on textual claims |
| **9. Confidence scoring** | Combine token-level uncertainty + task-type prior + cross-specialist agreement | Custom scoring module |
| **10. Response composition** | Controller LLM writes the final natural-language answer, citing evidence sources | Same controller LLM as stage 3 |
| **11. Visual evidence rendering** | Overlay bounding boxes / change masks / confidence heatmap on the georeferenced image in the UI | Leaflet/deck.gl map layer over the uploaded raster |
| **12. Execution trace + report** | Serialize full trace as JSON; render as collapsible UI panel; export as downloadable PDF/JSON report | FastAPI backend, `reportlab`/`weasyprint` for PDF |
| **13. Deployment/demo** | Backend (FastAPI) + orchestration graph + model-serving containers, runnable on a single high-VRAM consumer GPU or a modest cloud instance; fully offline-capable | Docker Compose, FastAPI, LangGraph, `vLLM` |

---

## 7. System Architecture

```
                         ┌─────────────────────────────┐
                         │        Web Frontend          │
                         │  (React + Leaflet map view)  │
                         │  upload · query · evidence   │
                         │  overlay · trace panel        │
                         └───────────────┬───────────────┘
                                         │ REST/WebSocket
                         ┌───────────────▼───────────────┐
                         │        FastAPI Gateway         │
                         └───────────────┬───────────────┘
                                         │
                 ┌───────────────────────▼────────────────────────┐
                 │            Agentic Orchestrator (graph)          │
                 │                                                   │
                 │  [Query Interpreter] → [Compatibility Validator] │
                 │            │                    │ (reject w/reason)
                 │            ▼                    │
                 │     [Specialist Router]◄─────────┘
                 │       │        │         │
                 │       ▼        ▼         ▼
                 │  ┌────────┐┌────────┐┌────────────┐
                 │  │Single- ││Change- ││ Fusion     │
                 │  │Image   ││VQA     │ Pipeline    │
                 │  │Spec.   ││Spec.   │(2-stage)    │
                 │  └───┬────┘└───┬────┘└─────┬──────┘
                 │      └────────┬┴────────────┘
                 │               ▼
                 │        [Verifier Node]
                 │               ▼
                 │   [Confidence & Trace Emitter]
                 │               ▼
                 │      [Response Composer]
                 └───────────────┬───────────────────┘
                                 ▼
                 Evidence-grounded answer + map overlay
                 + confidence score + downloadable report
```

**Component notes:**
- The **Specialist Router** table is the only place "which model runs" is decided, and it is a deterministic lookup, not a free-form LLM decision — this is what makes the execution trace reproducible and auditable.
- Model-serving is containerized independently of the orchestrator so specialists can be swapped/upgraded (e.g., a future dedicated segmentation-based change-map model) without touching the graph logic.
- The entire stack is designed to run **offline / on-prem**, with cloud LLM APIs wired in only as an optional, clearly-labeled fallback path for the public-benchmark demo — not the default path for anything resembling ISRO/SAC imagery.

---

## 8. Datasets

| Purpose | Dataset | Source / access | Feasibility notes |
|---|---|---|---|
| Mandatory fine-tuning (single-image VQA/caption/grounding, S1+S2 fusion cues) | **BigEarthNet.txt** | arXiv:2603.29630 (dataset release) | Large (464K pairs); for hackathon timeframe, train on a stratified subset (e.g., 15–20% of train split) sufficient to reproduce the LoRA recipe's benefit, given the recipe converges on ~2 GPU-days for the full set |
| Mandatory change-VQA fine-tuning/eval | **CDVQA** (from SECOND) | Public release per Yuan et al. 2022 | Manageable size (2,968 pairs, >122K QA); fully feasible to fine-tune and evaluate within timeframe |
| Single-image eval benchmark | **VRSBench** | Public (NeurIPS 2024 release) | Used strictly for held-out evaluation, not training, per PS intent |
| Single-image VQA eval benchmark | **RSVQA** (LR/HR) | Public | Secondary eval cross-check against BigEarthNet.txt's own VQA split |
| Optional change-mask training (stretch) | **LEVIR-CD** or **xBD** | Public | Only pursued if time remains after mandatory items; xBD additionally gives a disaster-response demo narrative relevant to ISRO's stated use cases |
| Domain-shift stress-testing (self-sourced, not for training) | A small number of **Cartosat-2S / RISAT-like public samples** (e.g., via Bhoonidhi/NRSC open data where available, or high-resolution optical + SAR proxies of comparable GSD such as any openly licensed sub-metre optical and X/C-band SAR tiles) | Public/ISRO open portals where accessible | Not used to train the model (would risk overfitting to a tiny sample) — used only to validate that the domain-shift normalization pipeline (§5, stage 5) behaves sensibly on higher-resolution, different-sensor input before the real ISRO/SAC evaluation |
| Final grading | **ISRO/SAC evaluation set** (Cartosat-2S + RISAT pairs) | Provided by organizers, annotations withheld | Cannot be trained on; system must generalize — this is exactly why §5's domain-shift mitigation is treated as a first-class design concern rather than an afterthought |

All primary datasets are open-source and match exactly what the PS names as mandatory/benchmark data — no dataset substitution risk.

---

## 9. Feasibility Assessment

Assuming a typical SIH structure — extensive preparation time before a ~36-hour on-site build/demo event — the realistic split is:

**Buildable with high confidence (core MVP):**
- Single fine-tuning run producing the multi-task specialist (VQA + captioning + grounding) on a BigEarthNet.txt subset — recipe is proven, compute-cheap, and reproducible from public papers' hyperparameters.
- CDVQA-based change-VQA/description specialist via the same LoRA recipe.
- Typed orchestration graph with Query Interpreter → Compatibility Validator → Router → Verifier → Composer — this is software engineering on top of well-understood graph-execution frameworks (LangGraph or a hand-rolled equivalent), not research risk.
- Structured two-stage optical-SAR fusion pipeline (§5.4) — feasible because it reuses the already-trained single-image specialist twice rather than requiring new fusion-specific training.
- Web UI with map-based evidence overlay, execution trace panel, and downloadable JSON/PDF report.
- Input validation against file format/CRS/modality/footprint.

**Realistic stretch goals (attempt if core MVP lands early):**
- Domain-shift stress test against a handful of higher-resolution/SAR proxy samples, with a documented before/after comparison from the normalization layer — even a small, honestly-reported experiment here is worth more to a judge than an unaddressed gap.
- Optional pixel-level change map generation (Siamese difference model) trained on LEVIR-CD/xBD.
- A lightweight complementarity-detector trained directly on BigEarthNet.txt's paired S1/S2 labels rather than a purely rule-based version.

**Explicitly out of scope / future work (do not attempt in-hackathon, say so honestly):**
- A fully end-to-end generative optical-SAR fusion VLM with dedicated cross-modal contrastive pretraining (MM-OVSeg-style) — this is a multi-week research effort, not a hackathon deliverable, and claiming otherwise would be the kind of overreach a technical judge will immediately probe and penalize.
- Any claim of matching or exceeding published SOTA numbers on VRSBench/CDVQA leaderboards outright — the honest target is "competitive, benchmarked, and clearly documented," not "state of the art," given the compute/time budget.
- Full production-grade geospatial data governance/security hardening (access control, audit logging beyond the execution trace, encryption at rest) — architecturally anticipated (offline-capable, self-hostable) but not fully implemented as a demo feature.

---

## 10. Pros / Cons / Risks

**Pros**
- Every mandatory functional-scope item maps to a specific, literature-benchmarked technique rather than an untested idea.
- Modular specialist design means a failure in one component (e.g., the stretch-goal change-map model) does not take down the mandatory pipeline.
- The orchestration design directly targets three separate scored evaluation rows (Input Validation, Agentic Orchestration, Execution Trace) as structural properties, not bolt-ons.
- Fully open-weight/offline-capable stack removes a governance objection a government evaluator might otherwise raise.

**Cons**
- More moving parts than a single-model solution — more integration surface, more that can break under demo pressure. Mitigation: keep the Specialist Router lookup table small and the graph shallow; test the full pipeline end-to-end early and often, not just individual specialists.
- The structured fusion pipeline (§5.4) is a genuine design bet: it is more explainable and safer than naive concatenation, but it has not been benchmarked in the literature the way single-image VQA has, so its numbers will be self-reported rather than comparable to a published baseline. We mitigate this by being explicit about this in the write-up rather than implying it's a solved, precedented technique.
- Fine-tuning even a 1B-class model requires real GPU time; if compute access during preparation is constrained, the fallback is to fine-tune on a smaller stratified BigEarthNet.txt subset and be transparent about the reduced training data in the execution/report output.

**Risks**
- **Domain shift (Sentinel → Cartosat/RISAT) is the top technical risk** for every team on this PS, not just ours; we treat it as first-class (§5, §8, §9) rather than discovering it during judging, but it remains a risk that cannot be fully eliminated without access to real ISRO/SAC-like training data, which the PS deliberately withholds.
- **Counting/magnitude/smallest-change questions will underperform** regardless of engineering effort, per every paper surveyed — the mitigation is honest confidence reporting, not pretending this weakness doesn't exist.
- **Grounding (bounding-box) accuracy is the hardest single-image task** across every benchmarked model in the survey (mIoU in the single digits to twenties even for strong models) — if grounding is demoed, it should be shown alongside its confidence score, not presented as uniformly reliable.

---

## 11. Differentiation Strategy

1. **Lead the demo with a validation failure, not a success.** Show the Compatibility Validator rejecting a malformed or physically inconsistent query (e.g., mismatched footprints, wrong modality for the requested task) with a clear, specific explanation — before showing a single successful answer. This is the single highest-leverage 30 seconds of the demo, because it is the one thing almost no competing team will have built.
2. **Name the domain-gap problem out loud, with numbers.** State plainly that BigEarthNet.txt trains on ~10 m Sentinel imagery while the ISRO/SAC evaluation set uses ~0.65–2 m Cartosat-2S optical and ~3 m RISAT SAR, show the mitigation pipeline, and show even a small, honestly-reported stress test. Judges evaluating "Remote-Sensing Adaptation" and "Overall System Performance" are very likely to ask about this directly; being the team with a rehearsed, technically grounded answer — rather than being caught flat-footed — is a real differentiator.
3. **Show the execution trace as a first-class UI artifact**, not a debug log — this directly targets the PS's "Execution Trace" and "Evidence & Visual Output" evaluation rows and visibly demonstrates that the system is not "just an LLM with a system prompt."
4. **State the governance angle explicitly**: this system is designed to run fully offline, on infrastructure ISRO/SAC controls, with no imagery leaving the deployment boundary by default — a small framing choice that signals awareness of who the actual customer is (a national space agency handling sensitive imagery), not just "a hackathon judge."
5. **Be the team with an honest limitations section.** Explicitly stating what does not work well (counting, fine-grained change magnitude, grounding precision) and why, backed by literature-documented failure modes rather than hand-waving, reads as engineering maturity to a technical panel — most AI-drafted competing proposals will only list strengths.
