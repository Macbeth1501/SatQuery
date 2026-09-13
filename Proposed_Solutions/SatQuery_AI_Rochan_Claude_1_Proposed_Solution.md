# SatQuery AI — Proposed Solution (SIH26167)
### An Agentic Vision-Language Assistant for Multimodal Remote Sensing Image Analysis

*Prepared as a competition-grade technical proposal for ISRO / Department of Space, Smart India Hackathon SIH26167.*

---

## 1. Executive Summary & Unique Selling Proposition (USP)

### 1.1 System Overview

SatQuery AI is not "one more remote-sensing VLM." It is an **agentic reasoning layer sitting above a registry of narrow, domain-fine-tuned specialist models**, each individually SOTA-competitive on its own task (single-image VQA, captioning, grounding, change-VQA, optical-SAR fusion), coordinated by an LLM-driven **orchestrator-with-verifier** that plans, validates, executes, cross-checks, and audits every response before it reaches the user.

The system accepts single images, cross-modal (optical+SAR) pairs, or bi-temporal pairs in GeoTIFF/TIFF/PNG/JPEG, accepts a free-text query, and returns a natural-language answer *grounded in explicit visual evidence* (bounding boxes, masks, difference maps) with a calibrated confidence score and a fully auditable execution trace — exactly the nine-step controller loop the problem statement mandates.

```
 User Query + Image(s)
        │
        ▼
 ┌─────────────────────┐
 │  Input Validator     │  format / modality / geo-registration / count checks
 └─────────┬───────────┘
           ▼
 ┌─────────────────────┐
 │  Orchestrator (LLM)  │  intent parse → task plan → tool selection
 └─────────┬───────────┘
           ▼
 ┌─────────────────────────────────────────────┐
 │        Specialist Tool Registry               │
 │  VQA · Caption · Ground · ChangeVQA · Fusion  │
 └─────────┬───────────────────────────────────┘
           ▼
 ┌─────────────────────┐
 │  Evidence Fusion &   │  cross-tool consistency check, confidence calibration
 │  Verifier Agent      │
 └─────────┬───────────┘
           ▼
 Grounded Answer + Visual Evidence + Confidence + Execution Trace + Report
```

### 1.2 Primary Technical Innovation & Competitive Moat

Every one of the ten surveyed papers (BigEarthNet.txt, reBEN, CDVQA, the Qwen change-VQA study, EarthDial, GeoChat, RS-LLaVA, the RS-VLM survey, MM-OVSeg, VRSBench) is a **single monolithic model or a single dataset**. None of them orchestrate. The literature survey's own cross-cutting synthesis (§12, point 3) states this explicitly: no existing system covers the full mandate, and this fragmentation is the direct justification for an agentic architecture. SatQuery AI's moat is built on four defensible pillars that go *beyond* what the survey recommends:

1. **Verifier-in-the-loop orchestration, not blind tool-calling.** Most "agentic RS" prototypes (RS-Agent, Remote Sensing ChatGPT, GeoLLM-Squad-style multi-agent systems) route a query to a tool and return its output directly. SatQuery AI adds a dedicated **Evidence Verifier Agent** that cross-checks specialist outputs against each other (e.g., does the fusion model's built-up mask agree with the VQA model's presence answer?) and against deterministic geometric sanity checks (does a grounding box lie within image bounds, does a change-ratio bucket match the pixel-level count from the change mask?) before answering — directly countering the documented failure mode that agentic RS systems "hallucinate tools" and lack grounding beyond RGB.
2. **Task-conditioned single backbone + parallel LoRA adapter bank**, not five separate monolithic models. Following the convergent recipe independently discovered across five papers in the survey (RS-InternVL, GeoChat, RS-LLaVA, the Qwen change-VQA study, MM-OVSeg) — freeze the vision backbone, adapt only via LoRA — SatQuery AI trains **one shared frozen vision-language backbone with a swappable LoRA adapter per task**, cutting storage, deployment, and GPU-memory cost by roughly the same 10,000× parameter / 3× memory factor the RS-VLM survey (Paper 9) reports for LoRA over full fine-tuning, while sidestepping the multi-task interference RS-LLaVA documents (§8.4: joint training helps on large diverse data, hurts on small/narrow data).
3. **A genuine generative optical-SAR fusion specialist**, which the survey explicitly flags (§14) as the one capability *with no ready-made precedent* in any of the ten papers — MM-OVSeg fuses SAR but only for closed-set segmentation, not language. SatQuery AI closes this gap with a two-stage design: an MM-OVSeg-style **Cross-Modal Unification (CMU) + Dual-Encoder Fusion (DEF)** module produces a structured land-cover/change signal (mask + per-class confidence), which is then **verbalized by the same LLM decoder used for VQA/captioning** — precisely the "structured signal → verbalization" pattern the survey identifies (§14) as the pragmatic solution, rather than attempting an unprecedented end-to-end pixel-to-language fusion model from scratch under hackathon time constraints.
4. **Confidence calibration informed by a documented, literature-wide weak spot**, not a generic softmax score. Every change-VQA and counting-adjacent result in the survey shows the same failure signature — quantity/counting/ratio-bucket questions score 30–60% versus 80–85% on binary/directional questions (CDVQA §4.6, Qwen change-VQA study §5.5, RS-LLaVA §8.4, VRSBench's 18%-of-questions "quantity" category). SatQuery AI's confidence module uses this as a **structural prior**, not just a post-hoc calibration curve — routing quantity-type queries through an explicit vision-count cross-check (rather than trusting the LLM's stated count) and lowering the reported confidence band by a fixed, empirically justified offset regardless of which specialist produced the answer.

### 1.3 What Makes This a Winning Entry, Not a Boilerplate

A generic "call GPT-4V with a system prompt" submission is explicitly disqualified by the problem statement, and the survey provides the empirical ammunition to prove why: GeoChat's un-fine-tuned baseline collapses from 46.7% to 13.9% BLEU-1 on captioning and from 76.0% to 40.8% on VQA the moment fine-tuning is removed (VRSBench §11.5); RS-InternVL's fine-tuned 1B model beats both larger generalist and existing RS-specialist VLMs by 15–50 points across every task (BigEarthNet.txt §2.6). SatQuery AI's technical write-up leads with these numbers as **evidence of why the mandatory fine-tuning constraint is not bureaucratic but empirically necessary**, then demonstrates its own reproduction of the same fine-tuning delta on the named benchmarks (VRSBench, RSVQA, CDVQA) as the core proof point in the demo.

---

## 2. Critical Evaluation of Prior Art & Web Insights

### 2.1 Flaws, Bottlenecks, and Edge-Case Failures in the Surveyed Literature

| Paper / System | Documented Flaw or Bottleneck | Consequence for a Naive Reuse |
|---|---|---|
| **GeoChat** (Kuckreja et al., 2024) | Single-image only; no temporal or SAR capability; weak on small objects / multi-box grounding (VRSBench §11.5: 49.8% Acc@0.5 is the *best* result in the field, and non-unique referents drop further to 44.5%) | Cannot be deployed alone — must be paired with change and fusion specialists; grounding confidence must be discounted for cluttered scenes with repeated object classes ("highlight the water body" when several exist) |
| **RS-LLaVA** (Bazi et al., 2024) | Multi-task joint training *helps* on large/diverse data but *hurts* on small/narrow datasets (13B model collapses to F1 49.94 on RSIVQA-DOTA presence detection under joint training); persistent, unresolved counting weakness | A single joint fine-tune across all SatQuery AI tasks risks the same collapse — mandates **per-task LoRA adapters**, not one multi-task head |
| **CDVQA baseline** (Yuan et al., 2022) | Only 0.1969 average accuracy under cross-dataset transfer (HTCD) versus 0.0601 random baseline — "better than chance but far from satisfactory"; naive subtraction/normalized-subtraction fusion underperforms concatenation | A change-VQA specialist trained only on CDVQA/SECOND cannot be assumed to transfer to Cartosat-2S/RISAT geometry and radiometry without explicit domain-adaptation data or synthetic bridging |
| **BigEarthNet.txt zero-shot evaluation** (Herzog et al., 2026) | Feeding extra SAR/multispectral channels into an RGB-pretrained backbone (EarthDial-S2, EarthMind-S1S2) shows **no consistent benefit and sometimes a regression** versus RGB-only variants of the same model | Any "just concatenate the SAR channel" implementation is an anti-pattern empirically falsified in the literature — genuine contrastive/attention-based fusion (CMU/DEF-style) is required, confirmed independently by reBEN's own fusion ablation (+0.30 points only from naive S1+S2 concatenation vs. +9.1 points from MM-OVSeg's DEF module) |
| **MM-OVSeg** (Wei et al., CVPR 2025) | Outputs pixel-wise segmentation only — no natural language; cross-domain generalization (DDHR-SK→DDHR-CH) degrades every method, MM-OVSeg included, even though it retains the largest margin | Cannot be used as a drop-in fusion-VQA tool; must be wrapped with a verbalization layer, and the ISRO/SAC Cartosat-2S+RISAT pair constitutes exactly this kind of cross-domain shift risk |
| **VRSBench** (Li et al., NeurIPS 2024) | Even the *best* grounder (fine-tuned GeoChat) reaches only 49.8% Acc@0.5 overall; GPT-4V without explicit object-attribute context scores a mere 5.1% | Region grounding is empirically the least mature of the three single-image tasks — the technical write-up should treat grounding as a demonstrable stretch capability and lean on captioning as the lower-risk "additional single-image task," matching the RS-VLM survey's own risk assessment (§9.6) |
| **Qwen Change-VQA study** (Bazi et al., 2026) | Scaling is *non-monotonic* — Qwen3-VL-8B underperforms the 4B variant on both CDVQA test splits under fixed-rank LoRA | Blindly picking "the biggest available backbone" is not a safe default; backbone size must be validated per-task rather than assumed monotonic with capability |
| **Agentic RS surveys** (Talemi et al., 2026; various 2025–26 arXiv works) | Documented, named failure modes across current agentic RS systems: **fragile tool orchestration (hallucinating tools), shallow temporal memory, fragmented evaluation protocols, and insufficient geospatial grounding beyond RGB** | Directly motivates SatQuery AI's Evidence Verifier Agent (§1.2, pillar 1) and its GeoValidator-style geometric sanity layer (§3.4.5) — these are not hypothetical risks, they are the field's current, named, unsolved problems |

### 2.2 Gap Analysis Incorporating Modern, State-of-the-Art External Research

Beyond the ten survey papers, current (2025–2026) work materially changes what a competitive submission should build:

- **Multi-agent RS orchestration is now an active research area, not a hypothetical.** A January 2026 survey (Talemi et al., arXiv:2601.01891) formalizes a taxonomy of "single-agent copilots" (RS-Agent, Remote Sensing ChatGPT) versus "multi-agent orchestrators," and systems such as **GeoLLM-Squad** demonstrate domain-specialized agents coordinated by a lightweight orchestrator achieving ~60% agentic task-completion accuracy on complex geospatial workflows — validating the problem statement's own architectural premise but also revealing that current systems still plateau far from reliable, motivating SatQuery AI's added verifier layer rather than a bare planner-executor loop.
- **GeoValidator-style reward/consistency layers.** Newer agentic-RS work (arXiv:2604.24919) explicitly proposes a "GeoValidator" component enforcing spatial consistency as part of the orchestrator's training loop (via reinforcement learning with geospatial-validity rewards), rather than only prompting an LLM to "be careful." SatQuery AI adopts this as a rule-based + learned verifier module rather than relying purely on prompting.
- **VLM confidence calibration has moved well past softmax scores.** Recent 2025–2026 work (VL-Calibration, arXiv:2604.09529; semantic-perturbation object-level calibration, arXiv:2504.14848; Hedge-Bench dense geometric entropy for VQA, Nov 2025) shows that **verbalized confidence from an uncalibrated VLM is frequently overconfident**, and that self-consistency / semantic-clustering-based uncertainty estimators (e.g., sampling multiple answer paraphrases and measuring semantic dispersion) substantially outperform a model's own stated confidence score. This directly informs SatQuery AI's confidence-estimation design (§3.4.6) — the system does not trust a specialist's self-reported confidence at face value.
- **RingMo-Agent and other 2025 unified RS foundation models** demonstrate that a single backbone can be conditioned via task tokens/prompts across multi-platform, multi-modal reasoning tasks — reinforcing (independently of GeoChat) that a **shared backbone + task-conditioning**, rather than N independent monolithic models, is now an emerging industry-standard pattern, not merely a hackathon shortcut.

### 2.3 Comparative Matrix — Existing Approaches vs. Proposed Solution

| Dimension | GeoChat | RS-LLaVA | EarthDial | CDVQA baseline | MM-OVSeg | **SatQuery AI (Proposed)** |
|---|---|---|---|---|---|---|
| Single-image VQA | ✔ | ✔ | ✔ | ✘ | ✘ | ✔ (task-conditioned LoRA adapter) |
| Captioning | Weak w/o fine-tune | ✔ | ✔ | ✘ | ✘ | ✔ |
| Region grounding | ✔ (best-in-class, still <50% Acc@0.5) | ✘ | Partial | ✘ | ✘ | ✔ + unique/non-unique disambiguation prompt |
| Bi-temporal change-VQA | ✘ | ✘ | Partial (MUDS captions only) | ✔ (closed-set) | ✘ | ✔ (open-ended, CEM-style attention + closed-set cross-check) |
| Optical-SAR fusion | ✘ | ✘ | ✔ (classification/captioning only) | ✘ | ✔ (segmentation only, no language) | ✔ (CMU+DEF mask → LLM verbalization) |
| Natural-language orchestration across tasks | ✘ (single model, single task per call) | ✘ | ✘ | ✘ | ✘ | ✔ (LLM planner + tool registry) |
| Cross-tool evidence verification | ✘ | ✘ | ✘ | ✘ | ✘ | ✔ (dedicated Verifier Agent) |
| Auditable execution trace | ✘ | ✘ | ✘ | ✘ | ✘ | ✔ (mandatory per problem statement) |
| Calibrated, uncertainty-aware confidence | ✘ | ✘ | ✘ | ✘ | ✘ | ✔ (semantic-dispersion based, not raw softmax) |
| Deployment footprint | 1 monolithic 7B model | 1 monolithic 7B/13B model | 1 monolithic 4B model | 1 task-specific CNN/Transformer | 1 segmentation model | 1 shared frozen backbone + swappable LoRA adapters (~10,000× fewer trainable params per task) |

---

## 3. Complete End-to-End Pipeline Architecture

### 3.1 Full System Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                                CLIENT / GUI LAYER                                  │
│  Web app (React) — image upload, query box, evidence viewer, report download       │
└───────────────────────────────────────┬────────────────────────────────────────────┘
                                         │  REST/GraphQL (multipart upload + JSON query)
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│                            API GATEWAY & SESSION LAYER                            │
│  Auth, rate limiting, request logging, async job queue (Celery/Redis)             │
└───────────────────────────────────────┬────────────────────────────────────────────┘
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 0 — INPUT VALIDATION & PREPROCESSING SERVICE                                │
│  • Format sniff (GDAL): GeoTIFF/TIFF/PNG/JPEG                                      │
│  • Modality detection (band count/order, S1 vs S2 vs Cartosat vs RISAT signature)  │
│  • Geo-registration check (CRS match, pixel-grid alignment, overlap %) for pairs   │
│  • Radiometric QC (cloud/snow/no-data mask %, histogram sanity)                    │
│  • Count/pairing validation (1 image / cross-modal pair / bi-temporal pair)        │
│  ⇒ emits a structured ValidationReport {ok|error, modality, pair_type, warnings}   │
└───────────────────────────────────────┬────────────────────────────────────────────┘
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1 — AGENTIC ORCHESTRATOR (LLM Planner, function-calling mode)               │
│  • Parses NL query → task intent (VQA / Caption / Ground / ChangeVQA / Fusion)     │
│  • Cross-references intent against ValidationReport (task feasible given inputs?) │
│  • Emits a structured ExecutionPlan: [ {tool, params}, {tool, params}, ... ]       │
│  • Plans MAY be multi-tool (e.g. fusion mask → then VQA over the fused evidence)   │
└───────────────────────────────────────┬────────────────────────────────────────────┘
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2 — SPECIALIST TOOL REGISTRY (shared frozen backbone + swappable LoRA)      │
│  ┌───────────┐ ┌───────────┐ ┌────────────┐ ┌───────────────┐ ┌─────────────────┐ │
│  │ VQA        │ │ Caption    │ │ Grounding  │ │ Change-VQA /   │ │ Optical-SAR      │ │
│  │ Adapter    │ │ Adapter    │ │ Adapter    │ │ Change-Desc    │ │ Fusion (CMU+DEF) │ │
│  │            │ │            │ │            │ │ Adapter + CEM  │ │ + Verbalizer     │ │
│  └───────────┘ └───────────┘ └────────────┘ └───────────────┘ └─────────────────┘ │
│                     shared frozen ViT/CLIP visual encoder(s)                        │
│                     shared frozen LLM decoder (LoRA-swapped per call)              │
└───────────────────────────────────────┬────────────────────────────────────────────┘
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3 — EVIDENCE FUSION & VERIFIER AGENT                                       │
│  • Cross-tool consistency check (geometric sanity, mask/answer agreement)         │
│  • Semantic-dispersion confidence estimation (multi-sample, cluster variance)     │
│  • Quantity/counting queries routed through deterministic pixel-count cross-check │
│  • Rule-based fallback / abstention if consistency check fails                   │
└───────────────────────────────────────┬────────────────────────────────────────────┘
                                         ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│  STAGE 4 — RESPONSE ASSEMBLY & AUDIT TRACE GENERATION                             │
│  • Natural-language answer + visual evidence (boxes/masks/change-maps)            │
│  • Confidence badge (calibrated, tiered: High / Medium / Low-quantitative)        │
│  • Execution summary: task, tool(s), params, model versions, timings              │
│  • Downloadable PDF/JSON report                                                    │
└───────────────────────────────────────┬────────────────────────────────────────────┘
                                         ▼
                                   CLIENT / GUI LAYER (render)

               ═══════ MLOps / Observability plane (cross-cutting) ═══════
   Model registry (MLflow) · Drift monitors · Prometheus/Grafana · CI/CD (GitHub Actions)
```

### 3.2 Data Ingestion & Preprocessing

**Training-side data engineering.**

- **Primary corpus:** BigEarthNet.txt (464,044 co-registered Sentinel-1/Sentinel-2 pairs, 9.6M text annotations across captioning, binary/MCQ VQA, and referring-expression tasks) is the mandated fine-tuning dataset and is used for the VQA, Captioning, and Grounding adapters, and as the visual-representation anchor for the Fusion specialist. The **BigEarthNet v2.0 official train/val/test split** (229,114/118,095/116,835 pairs) is respected as-is to keep results comparable to the survey's own reported numbers.
- **Practical download/storage layer:** reBEN's re-processed (sen2cor v2.11), pixel-accurately re-labeled, geographically-leakage-corrected version of the same S1+S2 imagery is used as the actual on-disk training corpus, converted via reBEN's `rico-hdl` tool into an LMDB/safetensors store for high-throughput random-batch reads — directly reusing reBEN's validated engineering rather than re-implementing a GeoTIFF data loader from scratch. reBEN's **concentric outer/middle/inner geographic split** (rather than a naive grid split) is adopted for any BigEarthNet-derived data used in fine-tuning, specifically to avoid the train/test leakage the original BigEarthNet split is documented to suffer from — this matters disproportionately here because the undisclosed ISRO/SAC evaluation set is an out-of-distribution domain shift test (Cartosat-2S/RISAT vs. Sentinel-1/2), so overstating in-distribution generalization is the single biggest risk to a fair self-assessment before submission.
- **Change-VQA corpus:** CDVQA (from the SECOND semantic change-detection dataset), 2,968 usable bi-temporal 512×512 pairs, >122,000 auto-generated QA pairs across five/eight question types (change-or-not, increase/decrease, change-to-what, largest/smallest change, change-ratio). Used verbatim per its official train/val/test1/test2 split, with **test2 retained as the harder, distribution-shifted evaluation split** rather than only reporting test1.
- **Optical-SAR fusion bridging data:** MM-OVSeg's CMU-Data (25,087 aligned, unlabeled RGB-SAR pairs from SpaceNet6 and DFC2023) is used to pretrain the SAR-side dense encoder via the same InfoNCE contrastive objective MM-OVSeg validates as the best-performing CMU loss (73.1% mIoU vs. 67.7% for MSE, 69.0% for L1, in MM-OVSeg's own ablation). BigEarthNet.txt's own co-registered S1/S2 pairs supply the *same-time* fusion supervision (not full bi-temporal), so the fusion pipeline is explicitly trained on **same-time cross-modal pairs**, matching the problem statement's "Cross-Modal Pair" input definition rather than conflating it with bi-temporal change.
- **Evaluation-only benchmarks:** VRSBench (29,614 images; captioning/grounding/VQA with unique-vs-non-unique grounding split and GPT-4-judged VQA semantic accuracy) and RSVQA (LR/HR closed-set VQA) are held out strictly for evaluation, never mixed into training splits, to keep reported numbers comparable to the problem statement's own named benchmarks.
- **Synthetic augmentation:** Because change-VQA and fusion transfer to the undisclosed Cartosat-2S/RISAT domain is the single largest identified risk (per the survey's own cross-dataset transfer finding of 0.1969 vs. 0.0601 accuracy for CDVQA→HTCD), a lightweight **domain-bridging augmentation stage** simulates plausible radiometric/resolution shifts (histogram matching toward Cartosat-2S's panchromatic/multispectral response curves, speckle-noise injection matching RISAT's SAR characteristics, GSD downsampling/upsampling) applied to a held-out slice of training data purely for **robustness stress-testing**, not for inflating headline accuracy — reported separately as a "domain-shift-robustness" ablation in the technical write-up.
- **Schema validation:** every ingested image (training or user-uploaded) passes through a strict schema check — CRS presence and validity, band count matching expected sensor signature, nodata percentage below a configurable threshold, and (for pairs) a minimum spatial-overlap and same-CRS check — modeled directly on reBEN's own patch QC pipeline (radiometric/geometric checks, cloud/snow flagging, minimum label-coverage threshold), repurposed here as the **Input Validation** component the agentic controller must run before dispatching any specialist tool.

### 3.3 Feature Engineering & Modality Alignment

- **Visual tokenization:** a frozen ViT/CLIP-style encoder (CLIP-ViT-L/14, following the convergent recipe independently validated by RS-LLaVA, GeoChat, and VRSBench's own baselines) produces patch embeddings for RGB/optical imagery. For multispectral (Sentinel-2 10m/20m bands, following BigEarthNet.txt's own finding that 60m bands carry limited semantic signal and are excluded) and SAR imagery, **modality-specific linear projection layers** (the RS-InternVL recipe) map sensor-specific patch embeddings into the same embedding space the frozen LLM decoder expects — this is the mechanism that lets one shared decoder consume RGB, multispectral, or SAR tokens interchangeably without retraining the decoder itself.
- **Cross-modal alignment (optical-SAR):** rather than naive channel concatenation — empirically falsified by BigEarthNet.txt's own zero-shot results (EarthDial-S2/EarthMind-S1S2 showing no consistent gain, sometimes regression, versus RGB-only) — the Fusion specialist uses **MM-OVSeg's two-stage CMU+DEF recipe**: Stage 1 aligns a learnable SAR DINO-style dense encoder to a frozen RGB DINO encoder via unsupervised InfoNCE contrastive loss on co-registered pairs; Stage 2 fuses CLIP global semantic embeddings with the CMU-aligned dense SAR/RGB features via a residual, convolution-gated fusion block, preserving CLIP's RGB-trained global semantic reasoning (which MM-OVSeg shows transfers to SAR without modification) while only adapting the *local/dense* pathway to the SAR domain.
- **Temporal alignment (bi-temporal change):** a Siamese-style shared-parameter encoder processes T1 and T2 images independently (`F1 = f(x_t1)`, `F2 = f(x_t2)`), followed by a **Change Enhancing Module (CEM)**, following CDVQA's own ablation showing concatenation-based fusion with an explicit difference-attention mechanism (`M_ce = σ(f_c(|f_q(F1) − f_k(F2)|))`) outperforms naive subtraction and improves average/overall accuracy (CDVQA's own reported 0.5766→0.6008 average-accuracy lift from adding CEM).
- **Task conditioning:** following GeoChat's task-token mechanism (`[vqa]`, `[caption]`, `[ground]`, `[change]`, `[fusion]` prepended to the instruction), the orchestrator's chosen tool is signaled to the shared backbone via an explicit task token *in addition to* selecting the corresponding LoRA adapter — giving two redundant, cross-checkable signals of task identity, which the Verifier Agent (§3.4.5) can use to detect adapter/prompt mismatches.
- **Grounding output schema:** bounding boxes are represented in GeoChat's clean, LLM-native textual format `{x_left, y_top, x_right, y_bottom | θ}` normalized to [0,100], with an explicit rotation angle θ to support oriented bounding boxes (VRSBench's OBB innovation) — necessary because Cartosat/RISAT imagery routinely contains rotated linear/areal features (roads, runways, field boundaries) poorly captured by horizontal-only boxes.

### 3.4 Core Inference Engine

#### 3.4.1 Backbone and Adaptation Strategy — Why LoRA-on-Frozen-Backbone Over Alternatives

The design decision that most determines the system's feasibility under hackathon time/compute constraints is the fine-tuning strategy. Three alternatives were considered:

| Strategy | Trainable Params | Compute Cost | Risk | Verdict |
|---|---|---|---|---|
| Full fine-tuning of a 7B+ VLM per task | 100% (~7–13B params) | Days on 8×A100/H100-class clusters per task; ×5 tasks = infeasible | High overfitting risk on RS-scale (still orders of magnitude smaller than web-scale) datasets, per the RS-VLM survey's own limitation (§9.5) | **Rejected** — compute-infeasible for a hackathon and empirically worse-justified than adapter methods |
| Adapter/prompt-tuning without LoRA (e.g., prefix-tuning, P-Tuning v2) | ~1–3% | Moderate | Historically weaker expressivity than LoRA for vision-language cross-attention adaptation in the surveyed literature; no survey paper reports this as best-in-class | **Rejected** — LoRA has direct, repeated empirical validation in this exact domain (5 independent papers) |
| **Frozen ViT/CLIP + frozen LLM + LoRA on attention projections (rank 8–64)** | **0.3–0.8%** (RS-InternVL: 5.8M/1.1B; Qwen change-VQA study: 0.3–0.8% across 0.8B–9B scale) | 1 epoch in ~2 GPU-days on 4×H200-class hardware (RS-InternVL's own reported cost) | Well-characterized failure modes (documented in this very survey), so risks are known and mitigable | **Selected** — independently converged upon by RS-InternVL, GeoChat, RS-LLaVA, and the Qwen change-VQA study; the RS-VLM survey explicitly recommends it citing 10,000× fewer trainable parameters and 3× lower GPU memory versus full fine-tuning |

**Backbone choice:** CLIP-ViT-L/14 (336×336, with GeoChat's interpolated-positional-encoding trick to support 504×504 for finer small-object grounding) is used as the shared frozen visual encoder for optical/RGB inputs, on the strength of it being the convergent choice across three independently developed systems (RS-LLaVA, GeoChat, VRSBench's own baselines). For the LLM decoder, a compact instruction-tuned model in the 2–4B parameter range is selected over a 7–13B model, directly following the Qwen change-VQA study's non-monotonic scaling finding (Qwen3-VL-8B underperforming the 4B variant under fixed-rank LoRA) and BigEarthNet.txt's own finding that a 1B fine-tuned model (RS-InternVL) beats every larger generalist and RS-specialist baseline it was compared against — **model scale is not the bottleneck; domain adaptation is**, and a smaller decoder also directly serves the system's P95 latency budget (§4.3).

**Adapter bank, not multi-task head:** rather than RS-LLaVA's single joint multi-task LoRA (which the survey's own §8.4 documents collapsing on small/narrow datasets — the RSIVQA-DOTA 13B joint model's F1 dropping to 49.94 on presence detection), SatQuery AI trains **one LoRA adapter per specialist task** (VQA, Captioning, Grounding, Change-VQA, Fusion-verbalization) on the shared frozen backbone. This sidesteps task interference entirely while the agentic controller — not the model itself — supplies the single-assistant user experience, exactly the architecture the problem statement's "multiple specialised components" language calls for.

#### 3.4.2 Task-Specific Objective Functions

| Specialist | Loss Function | Justification |
|---|---|---|
| VQA (binary/MCQ/open-ended) | Autoregressive next-token cross-entropy over the answer sequence, constrained at inference to the valid answer vocabulary for closed-set benchmarks (RSVQA) and left open-ended for BigEarthNet.txt/VRSBench-style free text | Matches the Qwen change-VQA study's own formulation: framing closed-set classification as constrained autoregressive generation lets one architecture serve both open-ended and benchmark-scoreable outputs |
| Captioning | Standard cross-entropy on caption tokens; evaluated with BLEU-1..4/METEOR/ROUGE-L/CIDEr plus CLAIR (GPT-4-judged) per VRSBench's protocol | n-gram metrics alone are known to poorly suit long, detailed captions (VRSBench §11.4) — CLAIR is included for evaluation only, not as a training signal (avoiding reward-hacking an LLM-judge during training) |
| Grounding | Cross-entropy over the tokenized bounding-box string `{x_left,y_top,x_right,y_bottom\|θ}`, i.e. box regression re-cast as sequence generation (GeoChat's approach) | Keeps the output head identical in kind to VQA/captioning (token generation), avoiding a separate detection-style regression head and associated NMS/anchor engineering |
| Change-VQA / Change-Description | Cross-entropy over the answer sequence, with the CEM's difference-attention map optimized jointly via the same end-to-end loss (no separate auxiliary loss term, following CDVQA's own architecture) | CDVQA's own ablation shows CEM's benefit is realized purely through improved feature representation, not a separate supervised target |
| Optical-SAR Fusion (CMU stage) | InfoNCE contrastive loss between RGB-DINO and SAR-DINO dense features on unlabeled co-registered pairs | MM-OVSeg's own ablation shows InfoNCE beats MSE (73.1% vs. 67.7% mIoU) and L1 (69.0%) for this exact alignment task |
| Optical-SAR Fusion (DEF + verbalization stage) | Pixel-wise cross-entropy for the structured mask/classification head (frozen CMU encoders); downstream caption/VQA cross-entropy for the LLM verbalizer consuming the mask + per-class confidence as structured input | Follows the survey's own recommended two-step pattern (§14) — a fusion classifier/segmenter produces a structured signal that is *then* verbalized by the shared LLM decoder, rather than requiring one model to natively fuse SAR/optical pixels and generate language end-to-end |

#### 3.4.3 Agentic Orchestration Logic

The orchestrator is implemented as an LLM operating in structured function-calling mode (tool-use), not free-form chain-of-thought — directly addressing the documented "fragile tool orchestration / hallucinating tools" failure mode named in current agentic-RS surveys (§2.2). Its responsibilities map one-to-one onto the problem statement's nine-step controller specification:

1. **Query interpretation & task classification** — the orchestrator classifies the query into one or more of {VQA, Caption, Ground, ChangeVQA, ChangeDesc, Fusion} using few-shot exemplars drawn from the representative queries in the problem statement itself (e.g., "Has the built-up area increased..." → ChangeVQA; "Use the optical and SAR images together..." → Fusion).
2. **Input validation cross-check** — the orchestrator receives the Stage-0 `ValidationReport` as structured context and refuses/reroutes any plan that requires inputs not present (e.g., a change-VQA request with only one image triggers a clarification response, not a hallucinated tool call).
3. **Model/tool selection** — selection is constrained to a **fixed, enumerable registry** (never a free-text tool name), eliminating the "hallucinated tool" failure mode by construction — the orchestrator can only emit tool identifiers that exist in a validated JSON schema.
4. **Parameter configuration** — only a small, explicitly whitelisted parameter set per tool is configurable by the orchestrator (e.g., IoU threshold for grounding, top-k for MCQ), following the problem statement's "configure only permitted task parameters" requirement, preventing prompt-injection-style parameter abuse from a crafted query.
5. **Execution** — tool calls are dispatched to the Stage-2 specialist registry; multi-tool plans (e.g., "use optical and SAR together to identify built-up regions" → Fusion tool produces a mask → VQA tool answers "which regions are built-up" conditioned on that mask) are executed in the orchestrator-specified sequence.
6. **Output combination** — textual and spatial outputs from possibly multiple tools are merged into a single structured `EvidenceBundle` object before verification.
7. **Confidence estimation** — handed to the dedicated Verifier Agent (§3.4.5–3.4.6), not computed by the orchestrator itself, to keep the confidence signal independent of the same LLM that made the tool-selection decision (avoiding a self-grading blind spot).
8. **Visual evidence return** — bounding boxes, masks, and change-difference maps are rendered as overlays on the original image(s) and attached to the response.
9. **Auditable execution summary** — every plan step, tool name/version, parameters, and output is logged verbatim into a structured trace object, per the problem statement's explicit note that *only the observable execution trace is evaluated*, not internal reasoning text — meaning the trace is engineered as a first-class structured output, not an incidental log scrape.

#### 3.4.4 Multi-Tool Plans for Compound Queries

Several representative queries in the problem statement require **more than one specialist**, which the orchestrator must sequence correctly:

- *"Use the optical and SAR images together to identify built-up and water-covered regions."* → Fusion tool (CMU+DEF mask) → verbalization pass describing built-up/water regions with mask-derived area statistics.
- *"Has the built-up area increased, decreased, or remained unchanged?"* → Change-VQA tool answering the direction question **and** a deterministic pixel-count cross-check against the change mask (if available) to validate the LLM's directional answer before it is returned — this is the concrete mechanism behind the "quantity queries get a deterministic cross-check" claim in §1.2.
- *"What changed between these two dates, and where did the change occur?"* → Change-Description tool (what) + Grounding-over-difference-map tool (where), combined into one narrative response with both a textual description and a spatial overlay.

#### 3.4.5 Evidence Verifier Agent — Cross-Tool Consistency Checking

This is SatQuery AI's principal architectural innovation beyond anything in the surveyed literature or the reviewed 2025–2026 agentic-RS systems. After the specialist registry returns an `EvidenceBundle`, the Verifier Agent runs three classes of checks before the response is finalized:

- **Geometric sanity checks (deterministic, rule-based):** grounding boxes must lie within image bounds; a change mask's spatial extent must not exceed the co-registered overlap region computed at Stage 0; oriented-box angles must fall within a plausible range. These require no ML and catch a large share of raw model errors cheaply — directly implementing the "GeoValidator" pattern recently proposed in agentic-RS research (arXiv:2604.24919) as a rule layer rather than purely a learned reward.
- **Cross-tool agreement checks:** e.g., if the Fusion tool's mask indicates 40% built-up coverage but the VQA tool (asked the same question independently, in an ensemble/self-consistency pass) answers "mostly agricultural," the disagreement is surfaced as a lowered confidence flag rather than silently resolved by picking one answer.
- **Deterministic cross-checks for quantity-type queries:** per the structural prior established in §1.2/§2.1 (counting/ratio questions are the field-wide weak point at 30–60% accuracy), any query classified as quantity-related is **never answered from the LLM's stated number alone** — wherever a mask or bounding-box set exists, a direct pixel/instance count is computed and compared against the LLM's stated answer; large discrepancies trigger an automatic "Low confidence — quantitative estimate" flag rather than a silent pass-through.

#### 3.4.6 Confidence Estimation — Beyond Raw Softmax

Following 2025–2026 findings that verbalized VLM confidence is frequently overconfident and that self-consistency/semantic-dispersion methods materially outperform a model's own stated confidence (VL-Calibration, arXiv:2604.09529; semantic-perturbation calibration, arXiv:2504.14848), SatQuery AI computes confidence via:

1. **Semantic-dispersion sampling:** for VQA/Change-VQA/Captioning, the specialist adapter is sampled *k* times (k=3–5, temperature >0) and the resulting answers are clustered by semantic equivalence (via lightweight embedding similarity); low dispersion (all samples agree) maps to high confidence, high dispersion maps to low confidence — this is materially more reliable than reading off a single softmax probability, per the cited 2025–2026 calibration literature.
2. **Structural discount for known weak-point query types:** any query type identified in the survey as a systematic weak point (quantity/counting, smallest-change discrimination, change-ratio bucketing) receives a fixed confidence-band discount *regardless* of the sampled dispersion, since these are documented failure modes that dispersion sampling alone does not fully surface (models can be *consistently* wrong).
3. **Verifier-agent override:** any geometric-sanity or cross-tool-agreement failure from §3.4.5 forces the confidence band down to "Low" irrespective of the above two signals, since a verifiable inconsistency is a stronger negative signal than model-internal uncertainty proxies.

Confidence is surfaced to the user as a three-tier badge (**High / Medium / Low**) rather than a raw numeric probability, since raw probabilities from a semantic-dispersion + rule-based blend are not meaningfully comparable to a calibrated Bayesian posterior, and a numeric-looking score risks implying false precision — an evenhanded, defensible design choice given the current state of VLM calibration research.

### 3.5 Post-Processing & Business Logic

- **Decision boundaries:** the orchestrator's task-classification step uses a confidence threshold on intent classification itself; below-threshold queries trigger a single clarifying question to the user (e.g., ambiguous "show me the image" queries with no clear task) rather than guessing and returning a low-quality answer.
- **Rule-based filtering:** grounding results below a minimum IoU-plausibility heuristic (extremely small or image-spanning boxes) are filtered before being shown, since these are a known low-precision failure mode (VRSBench §11.5 shows grounding is the least mature of the three single-image tasks).
- **Calibration:** the semantic-dispersion clustering threshold and structural discount magnitudes (§3.4.6) are tuned on the held-out validation splits of VRSBench/RSVQA/CDVQA, not on the test splits, to avoid leaking calibration information into the reported benchmark numbers.
- **Anomaly fallbacks:** if Stage-0 validation fails (unsupported format, missing co-registration, mismatched CRS) or if the Verifier Agent flags an unresolvable cross-tool disagreement, the system returns an explicit "cannot answer reliably" response with the specific reason, rather than forcing a best-effort guess — directly aligned with the "selective prediction / abstention" paradigm from the 2025 Reliable VQA Challenge literature (arXiv:2512.14770).

### 3.6 Serving & MLOps Infrastructure

- **API contract:** a versioned REST/GraphQL contract (`/v1/analyze`) accepting multipart image upload(s) + JSON query, returning a structured JSON response containing `{answer, evidence: {boxes, masks, overlays}, confidence: {tier, rationale}, execution_trace, report_url}` — the structured trace is a first-class response field, not an afterthought, per the problem statement's auditability requirement.
- **Model serving:** the frozen shared backbone is served once; LoRA adapters are hot-swapped per request via a lightweight adapter-loading layer (e.g., PEFT/vLLM multi-LoRA serving), avoiding the need to load five separate 2–4B models into memory simultaneously — a direct consequence of the shared-backbone architectural decision in §3.4.1, and the primary lever keeping GPU memory bounded to roughly one model's footprint plus a handful of small adapter deltas.
- **Inference optimization:** the vision encoder and LLM decoder are exported to ONNX/TensorRT with FP16 (and INT8 for the vision encoder, where accuracy loss is empirically negligible for classification/embedding-style tasks) to meet the P95 latency budget (§4.3); KV-cache reuse is enabled for multi-turn or multi-tool-in-one-query interactions.
- **Caching:** validation results and vision-encoder embeddings for a given uploaded image are cached (keyed on image hash) so that a follow-up query on the same image does not re-run Stage 0 or re-encode the image from scratch — a meaningful latency win for the common "ask several questions about the same pair" usage pattern.
- **CI/CD:** every LoRA adapter change is gated by an automated regression run against the held-out validation slices of VRSBench/RSVQA/CDVQA before promotion, with results logged to a model registry (e.g., MLflow) alongside the exact frozen/trainable parameter split and LoRA configuration (rank, target modules, α) — directly following the survey's own benchmark-alignment recommendation (§16) that judges evaluating "Remote-Sensing Adaptation" will look for this level of specificity.
- **Drift monitoring:** input-distribution monitors track band statistics, GSD, and CRS metadata of incoming production images against the training distribution; a sustained shift (e.g., a surge of Cartosat-2S/RISAT-domain queries during evaluation) triggers an alert to re-run the domain-shift-robustness ablation (§3.2) rather than silently degrading.

---

## 4. Datasets, Benchmarks & Feasibility

### 4.1 Target Datasets, Acquisition, and Licensing

| Dataset | Role | Access | Licensing Note |
|---|---|---|---|
| **BigEarthNet.txt** (arXiv:2603.29630) | Mandatory fine-tuning corpus — VQA, captioning, referring-expression | Open, arXiv-linked release | Open-source per problem statement's explicit statement that all datasets are open |
| **reBEN** (arXiv:2407.03653) | Practical download/storage layer for BigEarthNet-lineage imagery; pretrained backbones on Hugging Face (`BIFOLD-BigEarthNetv2-0`) | Open, Hugging Face + Copernicus Data Space Ecosystem re-download | CC-licensed per BigEarthNet lineage; Copernicus data is open and free |
| **CDVQA** (from SECOND) | Named benchmark — bi-temporal change-VQA training + evaluation | Open, arXiv:2112.06343 | Open academic release |
| **VRSBench** (NeurIPS 2024) | Named benchmark — captioning/grounding/VQA evaluation (held out, not trained on) | Open, NeurIPS Datasets & Benchmarks track | Open academic release |
| **RSVQA** (LR/HR) | Named benchmark — closed-set single-image VQA evaluation | Open | Open academic release |
| **MM-OVSeg CMU-Data** (SpaceNet6, DFC2023-derived) | Unlabeled RGB-SAR alignment pairs for the Fusion specialist's CMU stage | Open (SpaceNet6 CC-BY-SA, DFC2023 open contest data) | Compatible with open-source-only constraint |
| **ISRO/SAC evaluation set** (Cartosat-2S optical + RISAT SAR) | Final, undisclosed evaluation only — never used in training | Provided by organizers | Not used for training under any circumstance, per the problem statement's own non-disclosure of annotations |

No proprietary or closed dataset is used at any training stage, satisfying the problem statement's "open-source datasets only" framing while still assembling a corpus that covers every mandatory task.

### 4.2 Quantitative Evaluation Protocol

Following the survey's own Benchmark-Alignment Checklist (§16) verbatim, so that reported numbers are directly comparable to published baselines:

- **VQA:** VRSBench's GPT-4-judged semantic-accuracy protocol *and* RSVQA's per-question-type accuracy *and* BigEarthNet.txt's binary/MCQ accuracy split — three complementary protocols rather than one, so a single metric choice cannot flatter the result.
- **Captioning:** BLEU-1..4, METEOR, ROUGE-L, CIDEr at minimum; CLAIR (LLM-judged) reported alongside, given its known better fit for long, detailed captions versus n-gram metrics.
- **Grounding:** Accuracy@IoU {0.5, 0.7}, split by unique vs. non-unique referents (VRSBench's own methodological convention), with oriented-bounding-box accuracy reported separately given Cartosat/RISAT's oblique-geometry relevance.
- **Change-VQA:** CDVQA's per-question-type accuracy + Average Accuracy (AA) / Overall Accuracy (OA), directly benchmarked against the CDVQA baseline, VisTA, SOBA, and the Qwen3.5 numbers reported in the survey (VisTA: ~65.9/73.1 AA/OA on test1 is the bar to match or exceed).
- **Optical-SAR fusion:** an MM-OVSeg-style protocol adapted for generative tasks — matched clear-sky vs. cloud-contaminated conditions, intra-domain vs. cross-domain generalization, and (uniquely for SatQuery AI, since MM-OVSeg has no language output) a downstream VQA-over-fused-evidence accuracy score.
- **Remote-sensing adaptation evidence:** the exact frozen/trainable parameter split and LoRA configuration (rank, α, target modules) is documented per adapter, replicating the level of specificity every fine-tuning paper in the survey provides, since this is explicitly named as something judges will look for.

**Validation splits:** BigEarthNet.txt/reBEN's official geographic split is used for VQA/captioning/grounding; CDVQA's official train/val/test1/test2 split is used for change-VQA (test2 retained as the harder, distribution-shifted split rather than cherry-picking test1); VRSBench/RSVQA are held out entirely as evaluation-only benchmarks never touched during training, to avoid any test-set leakage claim.

**Baseline comparisons:** the technical report reproduces, at minimum, the un-fine-tuned vs. fine-tuned delta documented across the survey (GeoChat's 13.9→46.7 BLEU-1 collapse, RS-InternVL's 58.38→73.29 binary-VQA jump) as the headline ablation proving the mandatory adaptation requirement is met — not merely asserted.

### 4.3 Practical Implementation Constraints

| Constraint | Target / Budget | Justification |
|---|---|---|
| **Fine-tuning compute** | ~2 GPU-days per adapter on a single 4×H200-class node (or equivalent 4×A100 with longer wall-clock), following RS-InternVL's own reported cost for a comparable LoRA fine-tune | Keeps the full 5-adapter fine-tuning campaign feasible inside a multi-week hackathon build cycle without requiring a large GPU cluster |
| **Inference latency (P95)** | Single-image VQA/Caption: <3s; Grounding: <4s; Change-VQA (2 images): <6s; Fusion (2 images, CMU+DEF + verbalization): <8s | Sized around a 2–4B decoder with a frozen ViT-L/14 encoder, FP16/INT8-quantized and served via TensorRT/ONNX Runtime, consistent with published latency figures for comparably-sized VLMs under similar quantization |
| **Inference latency (P99)** | +50% over P95 targets, with a hard timeout returning a "still processing, partial evidence available" response rather than an unbounded hang | Protects the GUI's interactivity guarantee even under a cold-cache or multi-tool compound query |
| **Bandwidth / upload limits** | GeoTIFF up to ~200MB per image accepted via chunked multipart upload; PNG/JPEG (benchmark formats) capped at standard 512×512–1024×1024 sizes matching VRSBench/RSVQA conventions | GeoTIFF tiles for Cartosat-2S/RISAT-scale scenes can be large; chunked upload avoids request-size failures without requiring the user to pre-tile imagery |
| **Concurrent request handling** | Async job queue (Celery/Redis) with horizontal worker scaling; adapter hot-swap keeps GPU memory bounded to ~1 backbone + N small adapter deltas even under concurrent multi-task load | Avoids the naive "N separate monolithic models loaded simultaneously" memory blowup that a non-shared-backbone design would incur |
| **API rate limits (if any external LLM API is used for orchestration only, not for vision)** | Orchestrator calls are function-calling-only, single-turn per query in the common case, keeping external API cost/rate exposure minimal even if the orchestrator itself is served via a hosted LLM API rather than self-hosted | Keeps the *vision* pipeline fully self-hosted and auditable (a hard requirement given the mandatory fine-tuning/adaptation constraint), while allowing flexibility in how the *planning* layer is served |

---

## 5. Trade-Off Analysis & Risk Mitigation

### 5.1 Honest Pros and Cons

**Pros**

- Directly satisfies every mandatory requirement in the problem statement's Core Requirements Summary table, with each design choice traceable to a specific empirical finding in the survey or in current (2025–2026) external research rather than an unjustified default.
- The shared-backbone + swappable-LoRA architecture is dramatically cheaper to train and serve than five independent monolithic VLMs, making the full mandatory scope (VQA + one more single-image task + change analysis + fusion + orchestration) achievable inside realistic hackathon compute and timeline budgets.
- The Verifier Agent and structured, deterministic-cross-check design for quantity-type queries directly target the field's most consistently documented weak point (30–60% accuracy on counting/ratio questions across every relevant paper surveyed), rather than papering over it with an optimistic average.
- The execution-trace design treats auditability as a first-class structured output rather than an afterthought, matching the problem statement's explicit statement that only the observable trace — not internal reasoning — is evaluated.

**Cons**

- The optical-SAR fusion-to-language verbalization pipeline (§3.4.2, §1.2 pillar 3) has the least direct precedent of any component in the surveyed literature; it is the component most likely to underperform its target accuracy in the final evaluation, and should be treated as the highest-risk deliverable in project planning.
- Domain transfer from Sentinel-1/2 and SECOND/CDVQA's Chinese-city optical imagery to Cartosat-2S/RISAT is an acknowledged, literature-documented risk (CDVQA's own 0.1969 cross-dataset accuracy finding) — no amount of architectural cleverness fully substitutes for genuine target-domain training data, which is unavailable before submission since ISRO/SAC annotations are undisclosed.
- The multi-tool, multi-adapter orchestration adds real engineering surface area (adapter hot-swapping, structured tool schemas, verifier logic) compared to a single end-to-end model — more moving parts means more integration testing burden under hackathon time pressure.
- Confidence calibration via semantic-dispersion sampling requires multiple forward passes per query (k=3–5), directly trading off against the P95 latency budget in §4.3; this tension is real and is mitigated but not eliminated by only sampling k>1 for query types flagged as lower-confidence-prone.

### 5.2 Failure Modes, Edge-Case Vulnerabilities, and Contingencies

| Failure Mode | Trigger | Contingency |
|---|---|---|
| Fusion specialist underperforms on ISRO/SAC Cartosat/RISAT pairs | Domain gap between training-time SAR (Sentinel-1) and evaluation-time SAR (RISAT) radiometry/resolution | Fall back to the two-step "structured signal + verbalization" decomposition explicitly (mask-only output with a lower-confidence natural-language wrapper) rather than forcing a single confident fusion answer; report this fallback transparently in the execution trace |
| Grounding fails on cluttered, multi-instance scenes | VRSBench's own finding that non-unique-referent grounding is measurably harder (44.5% vs. 57.4% Acc@0.5 for unique referents) | Grounding responses for ambiguous referents return **all** plausible candidate boxes with per-box confidence rather than forcing a single top-1 answer, and the response text explicitly states the ambiguity |
| Quantity/counting query answered wrong with high stated confidence | Documented field-wide weak point; LLM self-reported confidence is known to be overconfident (2025–2026 calibration literature) | Deterministic pixel/instance cross-check (§3.4.5) forces a confidence downgrade whenever the LLM's stated count and the mask/box-derived count disagree beyond a tolerance band |
| Orchestrator selects wrong tool for an ambiguous query | Natural-language queries can be genuinely ambiguous between task types (e.g., "what's different here" could be change-description or fusion) | A below-threshold intent-classification confidence triggers a single clarifying question rather than a silent best-guess tool call |
| Input validation misses a subtly incompatible pair (e.g., mismatched CRS with small offset) | Georegistration errors are not always large enough to trip a coarse overlap-percentage check | Geometric sanity checks in the Verifier Agent (§3.4.5) act as a second line of defense after Stage 0, catching downstream symptoms (e.g., a change mask exceeding plausible bounds) even if the root input-validation check was insufficiently strict |
| Latency budget breached under compound multi-tool queries | A single query invoking Fusion → VQA sequentially can exceed the sum of both tools' individual P95 budgets | Hard P99 timeout returns partial evidence with an explicit "still processing" status rather than blocking the GUI indefinitely |
| LoRA adapter regression introduced by a later training run | Routine ML-engineering risk, compounded by the tight hackathon iteration cycle | CI/CD gate (§3.6) blocks promotion of any adapter that regresses on the held-out VRSBench/RSVQA/CDVQA validation slices versus the currently deployed adapter |

---

## 6. Hackathon Pitch & Presentation Strategy

### 6.1 The 30-Second Judge Pitch

> "Every existing remote-sensing AI system in the literature — GeoChat, RS-LLaVA, EarthDial, CDVQA, MM-OVSeg — does exactly one thing well. SatQuery AI is the orchestration layer that ISRO's own problem statement asks for: one shared, BigEarthNet-fine-tuned vision-language backbone with swappable task adapters, coordinated by an agentic controller that plans, executes, and — critically — **verifies its own specialists against each other** before answering. Ask it a single-image question, a 'what changed between these two dates' question, or a 'fuse optical and SAR to find the water body' question, and it routes to the right specialist, shows you the exact evidence — boxes, masks, difference maps — tells you how confident it actually is, using the same modern uncertainty-calibration research the field adopted in the last few months, not a raw softmax number, and hands you a fully auditable trace of every model it called. It's not a bigger model. It's the reliability layer no one else in this space has built yet."

### 6.2 Key Metrics and Impact Indicators for the Live Demo

- **The fine-tuning delta, shown live:** run the same query through the frozen, un-adapted backbone and then through the LoRA-adapted specialist side-by-side, reproducing the survey's own headline result (comparable in spirit to GeoChat's 13.9→46.7 BLEU-1 or RS-InternVL's 58.38→73.29 binary-VQA jump) — this is the single most persuasive, judge-legible proof that the mandatory adaptation requirement is genuinely met, not just claimed.
- **A deliberately ambiguous grounding query** ("highlight the water body" on a scene with two water bodies) to demonstrate the multi-candidate, confidence-flagged response rather than a silently wrong single box — showcasing the Verifier Agent's value directly.
- **A compound, multi-tool query** ("use optical and SAR together to identify built-up and water regions, then tell me if built-up area increased since the last pass") to show orchestration sequencing a Fusion call into a Change-VQA call and combining both into one coherent, evidence-backed answer.
- **The execution trace panel**, shown expanded during the demo, listing selected task, tool/model versions, parameters, and per-step timing — directly demonstrating the "auditable execution summary" the problem statement asks for as a first-class, structured UI element rather than a hidden log.
- **The confidence badge on a known-hard query type** (a change-ratio or counting question), deliberately shown returning a "Medium/Low" badge rather than a falsely confident answer — a concrete, honest demonstration that the system knows the documented boundaries of its own reliability, which is a rare and judge-impressive signal in a hackathon setting where most demos only ever show their best case.
- **Downloadable PDF/JSON report** generated live at the end of the demo, closing the loop on the "Downloadable Reports" expected deliverable.


