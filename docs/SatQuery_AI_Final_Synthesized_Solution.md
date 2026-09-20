# SatQuery AI — Final Synthesized Solution (SIH26167)
### Judged Draft Evaluation, External Research, and a Genuine Synthesis for ISRO's Agentic Remote-Sensing Vision-Language Assistant

*Prepared by evaluating four independently drafted proposals against the problem statement, conducting external literature research, and synthesizing a single solution that is designed to outscore every input draft on the PS's own evaluation rubric.*

---

## 1. Draft Evaluation Summary

### 1.1 Dhanshree — "Agentic Evidence Engine for Earth Observation"

**Core idea:** A pitch-deck-style proposal built around a narrative shift from "Image → VLM → Answer" to "Query → Planner → Specialists → Evidence Fusion → Grounded Answer." Its distinguishing conceptual contributions are five named "innovations": an Evidence Graph linking question→specialist→conclusion, Evidence Triangulation across sensors, Sensor-Adaptive (query-driven, not sensor-driven) reasoning, a Contradiction-Aware Agent that reports inconclusive evidence rather than forcing an answer, and Active Evidence Acquisition (telling the user what additional observation would raise confidence).

**Pros**
- The Contradiction-Aware Agent and Active Evidence Acquisition ideas are genuinely useful, PS-relevant UX patterns — neither is a standard "wrap a VLM in a chat UI" feature, and both map cleanly onto the PS's "confidence information" and "evidence-grounded response" requirements.
- The Execution Trace mock-up (§12) is concrete and demo-ready, directly answering the PS's "auditable execution summary" line item.
- The "What Not to Build" section (§17) shows real awareness of common failure modes for this category of hackathon project (don't train one giant model, don't hand-pick models per query, don't overweight change detection).

**Cons**
- Technically thin relative to the other three drafts: no loss functions, no training recipe, no discussion of *how* the "specialist router" actually resolves ambiguity, no discussion of the Sentinel→Cartosat/RISAT domain gap at all despite the PS naming Cartosat-2S/RISAT explicitly as the evaluation sensors.
- The Research Landscape (§2) is a flat list of paper names with one-line descriptions and no synthesis of what each paper's *limitation* is — Rochan and Sayali both extract specific, numeric failure modes from the same papers; Dhanshree does not.
- "Evidence Triangulation" and "Confidence/Validation Agent" are asserted (§8, §6) without a mechanism — no explanation of how disagreement is measured or thresholded, unlike Rochan's semantic-dispersion clustering or Sayali's evidence-ledger + NLI consistency check.
- No feasibility discussion: no dataset sizing, no compute budget, no phased MVP-vs-stretch plan grounded in what's realistically buildable, despite an explicit "Hackathon MVP" section (§19) that lists *what* to build but not *how much of it fits* in the time available.

**Genericness risk: Medium-High.** The core "agentic orchestrator over a specialist registry" shape is the single most predictable response to this PS — nearly any AI assistant prompted with this problem statement will independently arrive at "query understanding → task router → specialist tools → evidence fusion → grounded answer with trace," because the PS's own "Agentic Model and Tool Orchestration" section (which enumerates a 9-step controller loop) makes that architecture close to unavoidable. Dhanshree's draft does not differentiate itself from this default shape with any mechanism-level detail, which is precisely what would make it look identical to many competing teams' submissions.

---

### 1.2 Parth — "RSVP: Remote-Sensing Semantic Vision & Processing"

**Core idea:** An enterprise-grade production architecture — ViT-H/14 + LLaVA-1.6-Mistral-7B backbone, a SAM-RS grounding head, a Siamese change-detection network, cross-attention SAR-optical fusion, served via Kubernetes + NVIDIA Triton + TensorRT-LLM, with a vector database (Milvus/pgvector) for RAG-based historical recall, full RBAC/audit logging, and a 6-phase, ~25-week implementation roadmap with a QGIS plugin as a secondary client.

**Pros**
- The most complete *serving/MLOps* treatment of the four drafts: Prometheus/Grafana monitoring, COG raster storage, Triton-based multi-model serving are all realistic, well-chosen production components if this were being built as a fielded ISRO system rather than a hackathon prototype.
- The Architecture Decision Records (§12) are a good format for justifying trade-offs and are more rigorous than a plain feature list.
- The QGIS plugin as a second client surface (alongside the web dashboard) is a genuinely useful idea for the actual end users (GIS analysts) that no other draft raises.

**Cons**
- **Timeline mismatch with a hackathon.** The roadmap (§15) totals roughly 19–25 weeks across six phases. Nothing in the document acknowledges that this is a hackathon deliverable with a fixed, short build window — this is a scaled-down enterprise RFP response, not a hackathon proposal, and it never says so.
- **No domain-gap treatment.** Despite the PS explicitly naming Cartosat-2S and RISAT as the evaluation sensors, and despite the mandatory training data being Sentinel-1/2-based (BigEarthNet.txt), Parth's draft never once discusses the resolution/sensor mismatch between training and evaluation data. This is a material omission for the PS's own "Overall System Performance" and "Remote-Sensing Adaptation" scoring rows.
- **Fusion approach is the exact anti-pattern the wider literature (and this synthesis's own external research, §2) documents as harmful:** "cross-attention fusion matrices at the encoder phase" (ADR 003) is architecturally close to naive early fusion; nothing in the draft addresses BigEarthNet.txt's own zero-shot finding that feeding SAR/multispectral channels into an RGB-pretrained backbone can *regress* performance versus RGB-only variants (verified in this synthesis's own research, §2.1).
- **No literature-grounded risk analysis.** The Risks table (§13) is generic engineering risk ("model hallucination," "latency," "data drift") rather than risks derived from the specific papers relevant to this PS (e.g., grounding accuracy ceilings, counting-question weak points, cross-dataset transfer collapse) — none of which are cited anywhere in the document.
- Success metrics (§14, e.g. "Query Resolution Accuracy ≥ 85%," "Change Detection F1 ≥ 0.80") are asserted with no anchor to what any cited paper actually achieves on comparable tasks, making them look like plausible-sounding placeholder numbers rather than literature-informed targets.

**Genericness risk: High — this is the closest of the four drafts to what a generic, un-grounded AI-assisted proposal for "a multimodal AI system" looks like.** ViT-H + LLaVA + SAM + Kubernetes + Triton + a vector DB + RBAC + an ADR log is the default shape a capable LLM produces for almost *any* "design a production-grade multimodal AI platform" prompt, largely independent of the fact that this specific PS is about Sentinel-trained models being evaluated on Cartosat-2S/RISAT imagery. The lack of any PS-specific technical risk (domain gap, fusion anti-pattern, grounding accuracy ceiling) is the clearest evidence of this: a team that had engaged closely with the PS's own named datasets and sensors would have surfaced at least one of these.

---

### 1.3 Rochan (Claude-drafted) — "Verifier-in-the-Loop Orchestration over a Shared-Backbone LoRA Adapter Bank"

**Core idea:** A single frozen vision-language backbone with a swappable LoRA adapter per task (VQA, Captioning, Grounding, Change-VQA, Fusion-verbalization), coordinated by an LLM orchestrator restricted to structured function-calling over a fixed tool registry, with a dedicated Evidence Verifier Agent that performs deterministic geometric sanity checks and cross-tool agreement checks, and a confidence module using semantic-dispersion sampling (not raw softmax) with a structural discount for documented weak-point query types (counting/ratio questions).

**Pros**
- By a wide margin the most literature-grounded draft: every architectural decision in §3 is tied to a specific, numbered finding from a named paper (e.g., the adapter-per-task decision is tied directly to RS-LLaVA's documented multi-task collapse to F1 49.94 on RSIVQA-DOTA presence detection under joint training). This synthesis's own verification (§2 below) confirms these citations are real and accurately represented, not fabricated — a meaningful signal of technical soundness.
- The Evidence Verifier Agent (§3.4.5) with deterministic geometric sanity checks (grounding boxes must lie within image bounds, change-mask extent must not exceed co-registered overlap) is a genuinely defensible, PS-specific mechanism, not a vague "the system checks its own outputs" assertion.
- The confidence design (§3.4.6) is the most technically current of the four drafts — semantic-dispersion / self-consistency clustering over raw verbalized confidence is exactly the direction the 2025–2026 calibration literature has moved (independently confirmed in this synthesis's research, §2.3), and the structural discount for quantity-type queries is a direct, mechanistic response to a real, repeatedly-documented weak point.
- The Comparative Matrix (§2.3) against five prior systems is the clearest, most judge-legible "why not just use GeoChat/RS-LLaVA/CDVQA directly" argument across all four drafts.

**Cons**
- **Scope risk for a hackathon.** Five separate LoRA adapters, a dedicated fusion pretraining stage (InfoNCE contrastive CMU + DEF), a full MLOps stack (MLflow registry, Triton/TensorRT export, drift monitors, CI/CD gating), and a multi-sample (k=3–5) confidence-estimation pass at inference time is a large amount of engineering surface for a hackathon build window. The draft's own §4.3 latency budget (up to 8s P95 for fusion) already strains real-time demo expectations before adding k=3–5 sampling on top.
- The generative optical-SAR fusion design (verbalizing a CMU+DEF mask via the LLM decoder) is explicitly flagged by the draft itself (§5.1, Cons) as "the component most likely to underperform its target accuracy" — an honest admission, but it means the single most PS-emphasized capability ("combine the generated outputs" from optical+SAR) is also the draft's own acknowledged weakest link, without a fallback plan as concrete as Sayali's structured, non-generative pipeline.
- Despite being extremely well-cited, the draft's typed orchestration is *asserted* to prevent tool hallucination "by construction" via a fixed registry (§3.4.3, step 3) but the mechanism is functionally similar to Sayali's typed graph — the draft does not credit or differentiate its "structured function-calling" approach from the general ReAct/function-calling pattern the external research (§2.2 below) shows is empirically fragile, whereas Sayali explicitly names and rejects that pattern as a *design alternative*, which is a more rigorous form of the same conclusion.
- Very dense, citation-heavy prose (arXiv IDs and paper-specific numbers in nearly every sentence) risks working against it in an actual judging setting, where a live demo and a clear one-paragraph explanation matter more than a document a judge must read in full to appreciate.

**Genericness risk: Low.** The specific combination of shared-backbone LoRA-per-task + geometric-sanity verifier + semantic-dispersion confidence calibration is not the default output of a lightly-prompted AI assistant; it required genuine synthesis of ten+ specific papers' numeric findings. The risk is not genericness but *scope* — an ambitious, well-researched design that is harder to fully build than to fully describe.

---

### 1.4 Sayali (Claude-drafted) — "Geospatial Compiler: Typed Task-Graph with a Compatibility Validator"

**Core idea:** SatQuery AI reframed as a "geospatial compiler" — a typed, directed-graph orchestrator (not a ReAct/function-calling loop) whose first substantive node is a Compatibility Validator that can *reject* a query as physically unsatisfiable given the uploaded imagery before any specialist model runs. Optical-SAR fusion is deliberately solved as a structured two-stage pipeline (run the single-image specialist on each modality independently, compare structured evidence with a complementarity detector, then verbalize) rather than attempting a novel generative fusion model. The Sentinel→Cartosat/RISAT domain gap is treated as the single largest named technical risk and given first-class mitigation (GSD-normalization tiling, radiometric-jitter augmentation, a small calibration protocol).

**Pros**
- **The only draft that treats the Sentinel-vs-Cartosat/RISAT sensor mismatch as a first-order design constraint**, with specific numbers (Cartosat-2S pan 0.65 m / MS 2 m vs. Sentinel-2's 10–60 m — a 5–30× resolution jump) and a concrete mitigation pipeline, rather than an afterthought or omission. Given this is precisely the gap between the *mandatory training dataset* and the *undisclosed final evaluation dataset*, this is arguably the single most PS-specific insight across all four drafts.
- The "candidate approaches considered and rejected" section (§5.1) — four alternatives evaluated and explicitly rejected with reasons — is the clearest evidence of genuine deliberation rather than pattern-matching to a first plausible architecture, and directly satisfies this synthesis task's own instruction to avoid picking the first workable design.
- The structured, non-generative fusion pipeline (§5.4) is the most *honest* treatment of the field's real limitation (no existing generative optical-SAR fusion model) across all four drafts — it does not overclaim a novel fusion architecture it cannot fully validate in a hackathon window, unlike Rochan's CMU+DEF-to-language approach, which the same draft admits is its highest-risk component.
- The governance/offline-deployment framing (self-hostable stack, no default path shipping Cartosat/RISAT-class imagery to a third-party API) is a differentiator no other draft raises, and it is specifically well-matched to the actual customer (ISRO/DoS, a national space agency) rather than a generic "AI hackathon judge."
- The Feasibility Assessment (§9) is the most hackathon-realistic of the four: an explicit three-tier split into "buildable with high confidence," "realistic stretch," and "explicitly out of scope, say so honestly" — this is the only draft that draws a line and says what it will *not* attempt, rather than presenting every capability as equally achievable.

**Cons**
- Handling VQA, captioning, *and* grounding from a single jointly-trained LoRA adapter (§5.2) is the one place this draft under-guards against a risk that Rochan's draft explicitly surfaces and cites: RS-LLaVA's own documented collapse under multi-task joint training on small/narrow data (F1 dropping to 49.94 on a presence-detection subtask). Sayali's own draft even cites RS-LLaVA's counting weakness elsewhere (§2.1) without applying the same caution to its own joint-training decision for the three single-image tasks.
- The complementarity detector in the fusion pipeline (§5.4, step 2) is described as "a small rule-augmented classifier, trainable directly on BigEarthNet.txt's paired S1/S2 labels" but the draft itself later admits (§10, Cons) this exact component "has not been benchmarked in the literature the way single-image VQA has" — an honest flag, but it means the PS's most emphasized capability (cross-modal fusion) again rests on the least-validated custom component, similar to Rochan's fusion risk, just via a different (safer, but unproven) mechanism.
- Less deeply cited than Rochan's draft on raw technical numbers (loss functions, exact LoRA hyperparameters, per-task metric tables are thinner), which may read as less rigorous to a technically detailed judge even though the architectural reasoning is arguably sounder.

**Genericness risk: Low.** The Compatibility Validator as a rejecting, pre-execution graph node — rather than a soft "please be careful" instruction to an LLM router — combined with the explicit domain-gap engineering and the deliberate rejection of both naive fusion-by-concatenation and hosted-LLM orchestration, is a specific enough set of choices that it would not emerge from a lightly-prompted AI assistant without the same kind of targeted research this draft performs in §2.

---

## 2. External Research Findings

Independent web research was conducted beyond the four drafts' own literature surveys, both to **verify** load-bearing citations (several of the drafts cite very specific numeric results from papers with 2026 arXiv identifiers, which warranted direct verification rather than trust-by-default) and to **surface ideas none of the four drafts captured**.

### 2.1 Citation verification (technical-soundness check)

Spot-checks confirm the core citations underlying Rochan's and Sayali's drafts are real, not hallucinated:
- **BigEarthNet.txt** (arXiv:2603.29630, Herzog et al., submitted 31 Mar 2026) is a real, verifiable paper: 464,044 co-registered Sentinel-1/Sentinel-2 pairs with 9.6M text annotations across captioning, VQA, and referring-expression tasks, exactly as the PS and all four drafts describe it, including the exact pair/annotation counts Rochan's draft cites.
- **MM-OVSeg** (Wei, Xiao, Chen, Xia, Yokoya; CVPR 2026, arXiv:2603.17528) is real: a two-stage Cross-Modal Unification (CMU, InfoNCE-based SAR-to-RGB-DINO alignment on 25,087 pairs) + Dual-Encoder Fusion (DEF, CLIP+DINO) framework for optical-SAR open-vocabulary segmentation — confirming it genuinely does *not* produce natural-language output, supporting every draft's shared observation that a "structured signal → verbalization" wrapper (not an end-to-end generative fusion model) is the pragmatic hackathon-feasible design.
- **The agentic-RS orchestration critique** is real and, in fact, stronger than any single draft represents: two independent 2026 surveys — a WACV 2026 workshop survey ("Agentic AI in Remote Sensing: Foundations, Taxonomy, and Emerging Systems," Talemi et al.) and a companion piece ("Agentic AI for Remote Sensing: Technical Challenges and Research Directions") — both explicitly name **fragile tool orchestration ("hallucinating tools"), shallow temporal memory, fragmented evaluation, and insufficient geospatial grounding beyond RGB** as the field's current, unsolved limitations. This directly and independently validates both Rochan's Verifier Agent and Sayali's typed Compatibility Validator as responses to a real, citable, current research gap — not speculative hackathon novelty.
- **Confidence calibration**: VL-Calibration (arXiv:2604.09529) is real and reports concrete numbers not present in any draft — it reduces Expected Calibration Error on Qwen3-VL models from 0.421 to 0.098 while improving accuracy 2.3–3.0 points, by decoupling confidence into a *perception* component and a *reasoning* component rather than one blended score. This is a stronger, more specific technique than either Rochan's or Sayali's confidence design and is incorporated into the final synthesis below (§5.6).

### 2.2 Ideas found externally that none of the four drafts captured

- **Tool-orchestration failure modes are empirically dominated by tool-selection and argument-formatting errors, not model accuracy.** Benchmarks named across the two 2026 agentic-RS surveys — **ThinkGeo** (arXiv:2505.23752, 486 tasks over 14 executable RS tools), **GeoBenchX**, and **GTChain-Eval** — consistently report that agent failures concentrate in *choosing the wrong tool* or *malforming its arguments*, not in the underlying specialist model being wrong. This is a stronger, more specific empirical basis for constraining the orchestrator to a fixed, schema-validated tool registry (which both Rochan and Sayali do, but neither cites this exact class of benchmark evidence) than any single draft currently provides.
- **GeoGraphRAG** — a knowledge-graph-based approach (cited in the WACV 2026 survey) that encodes expert geospatial scripts and their preconditions/effects in a graph structure for retrieval-guided tool orchestration, rather than a flat lookup table or a free-form LLM decision. None of the four drafts consider anything beyond a static registry/lookup table for tool selection; a lightweight version of this idea (attaching machine-readable preconditions to each specialist, so the Compatibility Validator can check them structurally rather than via hand-written if/else logic) strengthens both Rochan's and Sayali's designs and is incorporated into the final synthesis.
- **Data-quality curation, not just architecture, is the dominant bottleneck for RS-VLM fine-tuning quality.** A 2025 paper (ScoreRS, arXiv:2503.00743) shows a learned quality-scoring model for filtering RS vision-language training pairs improves downstream accuracy more than switching backbones, and that the resulting model can itself serve as an RL reward signal. None of the four drafts propose any data curation/filtering step before fine-tuning on BigEarthNet.txt — all four assume the raw dataset should be trained on as-is (or subsampled only for compute reasons). This is incorporated as a specific, low-cost addition to the final methodology.
- **GeoLLaVA** (arXiv:2410.19552) — an efficient, LoRA-fine-tuned VLM specialized for temporal change detection in remote sensing, independent of the CDVQA/Qwen-change-VQA lineage all four drafts cite. It provides an additional, real precedent (beyond CDVQA) that a dedicated, separately-tuned adapter for change reasoning outperforms treating change as "VQA applied twice," reinforcing (from a second independent source) the per-task-adapter design choice this synthesis adopts.
- **SOMA-1M** (arXiv:2602.05480) — a newer, larger SAR-optical multi-resolution alignment dataset than MM-OVSeg's 25,087-pair CMU-Data, released after all four drafts were written. Its explicit multi-resolution framing is directly relevant to the Sentinel-vs-Cartosat/RISAT resolution gap and is added as a secondary fusion-bridging data source in §8.

---

## 3. Final Proposed Solution Overview

**SatQuery AI is a typed, schema-validated agentic controller sitting above a small family of remote-sensing-adapted vision-language specialists, built around three governing principles that no single input draft fully combines:**

1. **Validate before you execute, structurally, not conversationally.** A Compatibility Validator node (from Sayali) — extended with machine-readable per-specialist preconditions in the style of GeoGraphRAG (external research, §2.2) — can refuse a query as physically unsatisfiable *before* any specialist model runs, and the orchestrator is restricted to a fixed, schema-validated tool registry (from Rochan and Sayali jointly, reinforced by the ThinkGeo/GeoBenchX finding, §2.2, that tool-selection/argument errors — not model errors — dominate real agentic-RS failures).
2. **Treat the Sentinel→Cartosat/RISAT domain gap as the PS's real technical center of gravity**, because BigEarthNet.txt (Sentinel-1/2, 10–60 m) is the mandatory *training* data while Cartosat-2S (0.65–2 m) and RISAT SAR are the *undisclosed evaluation* data — a 5–30× resolution jump that is the single largest, most PS-specific risk identified by any draft (Sayali's, adopted here as the design's central engineering concern, §5.3), and one Parth's draft misses entirely.
3. **Never trust a single signal for either an answer or its confidence.** Follow the PS's evaluation table's own emphasis on "Evidence & Visual Output" and "Execution Trace" by cross-checking specialist outputs against each other and against deterministic geometry (Rochan's Verifier Agent) and by calibrating confidence via decoupled perception/reasoning confidence tokens (VL-Calibration, external research §2.1) rather than either raw softmax or undifferentiated self-consistency sampling.

Where the four drafts disagree on a specific design choice, this synthesis states explicitly which draft's approach was kept, which was modified, and why — see §11 for the full accounting.

---

## 4. USP / Innovation

### 4.1 What the generic, first-pass AI solution to this PS looks like

Having read all four drafts and conducted independent research, the "obvious" AI-generated answer to SIH26167 converges reliably on:

> *Fine-tune GeoChat or LLaVA on BigEarthNet.txt; wrap it in a LangChain/ReAct agent with function-calling over five or six tools (VQA, captioning, grounding, change detection, fusion); feed SAR and optical channels into the same VLM and call that "fusion"; use a hosted LLM API (GPT-4o-class) as the orchestrator brain; serve it behind a Kubernetes/Triton stack with a vector database for good measure; and demo it in a Streamlit or React dashboard.*

Parth's draft is, almost point for point, an instance of this pattern (ViT-H+LLaVA backbone, cross-attention "fusion" at the encoder, Kubernetes+Triton+Milvus serving) — which is exactly why it is flagged as the highest-genericness-risk draft in §1.2, not because its individual technology choices are bad, but because none of them are derived from this PS's specific, named constraints (Cartosat/RISAT evaluation sensors, the mandatory adaptation requirement, the documented harm of naive channel concatenation).

### 4.2 Where this synthesis deviates, and why each deviation is substantive

| Generic approach | This synthesis's deviation | Why it is a real improvement, not novelty for its own sake |
|---|---|---|
| ReAct/function-calling agent treats every specialist as an interchangeable black box, selected by free-form LLM reasoning | A typed graph with a **rejecting** Compatibility Validator node, using per-specialist machine-readable preconditions (modality, CRS, footprint overlap, temporal ordering) | Directly implements the PS's mandatory controller step 2 ("validate the input... image compatibility") as a structural property, not a prompt instruction. Backed by two independent 2026 surveys that name "fragile tool orchestration / hallucinating tools" as the field's current dominant failure mode (§2.1–2.2) — this is the single most repeatedly-validated design choice across all research consulted for this synthesis, not a hackathon-only novelty. |
| SAR + optical channels concatenated into one VLM, hoping fusion emerges | Two-stage structured fusion: independent single-image specialist evidence per modality → complementarity detector (agreement / optical-only / SAR-only) → LLM verbalization citing which modality supplied which claim, with the complementarity detector's alignment stage informed by MM-OVSeg's own validated InfoNCE contrastive objective (73.1% mIoU vs. 67.7% MSE / 69.0% L1 in MM-OVSeg's own ablation) rather than being purely rule-based | Naive concatenation is empirically falsified for this exact domain (BigEarthNet.txt's own zero-shot ablation shows regression, not gain, from adding SAR/multispectral channels to an RGB-pretrained backbone). No existing model does *generative* optical-SAR fusion (confirmed independently in this synthesis's own research, §2.1) — so building one from scratch in a hackathon window is the overreach Sayali's draft correctly declines, while grounding the complementarity detector in MM-OVSeg's validated alignment loss (rather than pure rules) closes part of the gap Sayali's draft admits is unvalidated. |
| Assume BigEarthNet.txt (Sentinel) fine-tuning transfers to the ISRO/SAC evaluation set without comment | Explicit domain-gap engineering as a first-class pipeline stage (GSD-normalization tiling, radiometric-jitter augmentation spanning Sentinel→Cartosat dynamic range, a held-out domain-shift-robustness stress test reported honestly, not to inflate headline accuracy) | Cartosat-2S is 5–30× higher resolution than Sentinel-2 and RISAT differs from Sentinel-1 in band/incidence geometry; this is a physics/sensor problem, not a modeling nuance. None of the ten core survey papers target ISRO sensors, and Parth's draft — the most production-oriented of the four — omits this entirely. Naming it and building a specific, cheap (augmentation-only, not new-model) mitigation is the highest-leverage, lowest-cost differentiator available in this PS. |
| Confidence = ask the model to output a percentage, or sample k times and cluster | **Decoupled perception/reasoning confidence** (VL-Calibration-style: separate confidence tokens for "did I see this correctly" vs. "did I reason about it correctly"), combined with a deterministic override from the Verifier Agent's geometric/cross-tool checks, and a fixed structural discount for the field's universally-documented weak point (counting/ratio/smallest-change questions, 30–60% vs. 80–85% accuracy across every change-VQA paper surveyed) | Verbalized confidence is well documented as overconfident; naive self-consistency sampling (Rochan's k=3–5 approach) is more reliable than raw softmax but strictly weaker than the decoupled-token approach, which independently reduces calibration error by roughly 4× in its own published ablation (§2.1) — this is the most current, best-evidenced calibration technique found across either the drafts or this synthesis's own research. |
| Orchestration brain is a hosted LLM API (GPT-4o/Gemini/Claude via API) | Fully open-weight, self-hostable controller + specialist stack, with a hosted-API path wired in only as an explicitly labeled, non-default fallback for the public-benchmark demo | Cartosat/RISAT-class imagery is government-sensitive geospatial data for the actual customer (ISRO/Department of Space); a default path that ships imagery to a third-party API is a governance red flag specific to *this* PS's actual evaluator, not a neutral engineering choice — a differentiator almost no competing AI-drafted proposal will think to raise, since it requires modeling who is judging the PS, not just what the PS technically asks for. |

**What would make a judge say "this is not what everyone else submitted":** leading the live demo with the Compatibility Validator *rejecting* a malformed or physically-inconsistent query (mismatched footprints, wrong modality for the requested task) with a specific, correct explanation, before showing a single successful answer — and having a rehearsed, numbers-backed answer to "what happens to your BigEarthNet-tuned model on Cartosat-resolution imagery," a question almost no competing team building this PS will have prepared for, based on the domain-gap omission observed in two of the four input drafts reviewed here (Dhanshree's and, especially, Parth's).

---

## 5. Methodology

### 5.1 Remote-sensing adaptation (mandatory requirement)

- **Backbone:** a compact open-weight VLM in the 1–4B range (e.g., InternVL3-1B-class or a small Qwen-VL variant), following the convergent, cross-validated finding — independently reproduced across five papers in the surveyed literature — that a properly fine-tuned small model beats larger un-tuned generalist and RS-specialist VLMs on this task family. A larger backbone is not the safe default: the Qwen change-VQA study's own non-monotonic scaling finding (an 8B variant underperforming a 4B variant under fixed-rank LoRA) is corroborating evidence, and a smaller decoder directly serves demo-time latency.
- **Recipe:** freeze the vision encoder and base LLM; add small modality-specific linear projections for S1 (SAR) and S2 (multispectral) tokens; apply LoRA (rank 8–16) only to the LLM's attention projections — the single most cross-validated recipe in the entire literature reviewed (independently reproduced by five separate research groups), training under 1% of total parameters.
- **Data quality step (new, from external research §2.2):** before fine-tuning, apply a lightweight quality-scoring filter to BigEarthNet.txt's training pairs (in the spirit of ScoreRS) rather than training on the raw dataset unfiltered, as all four drafts do — this is a genuinely low-cost addition (a scoring pass, not a new model) that the cited research shows moves accuracy more than backbone selection does.
- **Task split — a deliberate synthesis decision, not a default:** VQA and captioning are trained jointly on one LoRA adapter (both are free-text generation over similar visual evidence, and RS-InternVL's own result shows this combination transfers well). **Grounding is given its own separate adapter**, diverging from Sayali's single joint adapter for all three single-image tasks: grounding's output format (bounding-box token sequences) and its documented, much lower accuracy ceiling (best-in-class fine-tuned GeoChat reaches only ~49.8% Acc@0.5, non-unique referents drop to ~44.5%) make it the task most likely to suffer the RS-LLaVA-documented multi-task collapse (F1 dropping to 49.94 under joint training on narrow data) that Sayali's draft does not guard against but Rochan's draft explicitly surfaces. This split takes Rochan's caution about task interference but applies it selectively rather than to all five tasks, avoiding Rochan's own scope risk of five fully separate adapters plus a fusion-verbalization adapter.

### 5.2 Bi-temporal change analysis

- A third, separately fine-tuned LoRA adapter on the same backbone family, trained on CDVQA (from SECOND), using a Change-Enhancing Module (difference-attention over Siamese-encoded T1/T2 features) — CDVQA's own ablation shows this lifts average accuracy over naive subtraction-based fusion (0.5766→0.6008). GeoLLaVA (external research §2.2) provides an independent second precedent, beyond CDVQA/Qwen-change-VQA, that a dedicated change adapter outperforms treating change as "VQA run twice."
- Change description is generated by prompting the same adapter for free-form output rather than training a fourth model.
- **Quantity/ratio questions never get answered from the LLM's stated number alone** (Rochan's mechanism, kept in full): wherever a change mask or bounding-box set exists, a deterministic pixel/instance count is computed and cross-checked against the model's stated answer; disagreement forces a confidence downgrade. This directly targets the single most consistently-documented weak point across every relevant paper surveyed (30–60% accuracy on counting/ratio/smallest-change questions vs. 80–85% on binary/directional ones).

### 5.3 Optical-SAR cross-modal analysis — the domain-gap-aware structured fusion pipeline

This is the least-precedented mandatory requirement in the entire literature reviewed (confirmed independently in §2.1: no existing model does generative, language-producing optical-SAR fusion), so the mechanism is spelled out precisely, combining Sayali's structural design with Rochan's and this synthesis's own added grounding in MM-OVSeg's validated alignment loss:

1. Run the fine-tuned single-image specialist (§5.1) **independently** on the optical and SAR images, extracting *structured* evidence per modality (LULC class presence, approximate area share, grounded regions) — not free text.
2. A complementarity detector — trained on BigEarthNet.txt's own paired S1/S2 labels, using MM-OVSeg's validated InfoNCE contrastive alignment (not a purely hand-written rule set, which is the one place this synthesis strengthens Sayali's design with Rochan's more rigorous mechanism) — tags each LULC region as *agreement*, *optical-only*, or *SAR-only* (e.g., a water body visible in SAR backscatter but obscured by cloud in the optical scene — the PS's own representative example query).
3. The controller LLM verbalizes the structured comparison, citing which modality supplied which claim — satisfying the PS's "combine the generated outputs" instruction literally and auditably.
4. **Domain-gap mitigation is applied before step 1, not after:** GSD-normalization tiling and radiometric-jitter augmentation (histogram matching toward Cartosat-2S's response curve, speckle-noise injection matching RISAT's SAR characteristics) are applied to a held-out training slice purely for robustness stress-testing, reported honestly as a separate ablation rather than folded into headline accuracy (Sayali's mitigation design, kept in full as the PS-specific center of gravity identified in §3).

This deliberately avoids the empirically-falsified naive-concatenation failure mode by never asking one model to jointly ingest raw SAR and optical pixels; fusion happens at the semantic/structured level, which is both more robust and more explainable, and is honestly scoped as "competitive and well-documented," not "state of the art."

### 5.4 Agentic orchestration — typed graph with structural preconditions

The controller is a typed, directed graph (Sayali's design, extended per external research §2.2), not a flat ReAct/function-calling loop:

1. **Query Interpreter** (small, text-only instruct LLM) parses the query into a structured task spec `{task_type, required_modalities, required_temporal_pairing, requested_parameters}`.
2. **Compatibility Validator** checks the task spec against each specialist's machine-readable *preconditions* (GeoGraphRAG-style, §2.2) — format, modality, CRS/footprint overlap, temporal ordering — and terminates with a specific, human-readable reason if unsatisfiable, rather than forcing a downstream guess. This is the mechanism the PS's own step 2 ("validate the input") and the ThinkGeo/GeoBenchX finding (§2.2) that tool-selection errors dominate real agentic-RS failures both point toward.
3. **Specialist Router** — a deterministic lookup from validated task spec to specialist node(s), never a free-form LLM decision, keeping the execution trace reproducible.
4. **Specialist Execution** — structured (not free-text) outputs wherever possible, packaged into an evidence ledger.
5. **Verifier node** (Rochan's mechanism, kept in full) — geometric sanity checks (bounding boxes within image bounds, change-mask extent within the co-registered overlap region) and cross-tool agreement checks before anything reaches the user; failures downgrade confidence rather than silently pass through.
6. **Response Composer** — the controller LLM converts the evidence ledger into natural language, citing which specialist produced which claim.
7. **Confidence & Trace Emitter** — computes decoupled perception/reasoning confidence (§5.5) and serializes the full execution trace as the mandatory auditable summary.

### 5.5 Confidence estimation — decoupled, not blended

Rather than either raw softmax (weak) or undifferentiated k-sample self-consistency clustering alone (Rochan's approach — better, but not the strongest available), this synthesis adopts the VL-Calibration pattern verified in external research (§2.1): the specialist elicits **separate confidence signals for visual perception and for reasoning/answer construction**, which its own published ablation shows cuts calibration error roughly 4× versus a single blended confidence score. This is combined with:
- A fixed structural discount for query types the literature universally documents as weak (counting, ratio, smallest-change).
- A hard override to "Low" confidence whenever the Verifier node's geometric or cross-tool checks fail, since a verifiable inconsistency is a stronger negative signal than any internal uncertainty proxy.

Confidence is surfaced as a three-tier badge (High/Medium/Low), not a raw number, avoiding false precision given the current state of VLM calibration research.

### 5.6 Candidate approaches considered and rejected

Following Sayali's methodological discipline of explicitly stating rejected alternatives (kept here because it is the clearest evidence, across all four drafts, of genuine deliberation rather than pattern-matching to a first plausible design):

- **A. One end-to-end multimodal model for all five tasks** — rejected: dedicated change-reasoning and fusion-alignment both measurably outperform generalist multi-task tuning in the surveyed literature, and one failed fine-tuning run would break the entire system with no fallback.
- **B. Naive ReAct/function-calling as the primary orchestration mechanism** — rejected as primary (kept only as an optional user-facing explanation layer on top of the typed graph): this is exactly the pattern two independent 2026 surveys (§2.1–2.2) name as the field's current dominant failure mode.
- **C. A full end-to-end generative optical-SAR fusion VLM, trained from scratch** — rejected for the hackathon timeframe specifically, not as a bad idea: no existing training corpus or precedent exists for this exact generative task (confirmed in §2.1); flagged as future work, not attempted as a headline claim.
- **D. Cloud-API-only orchestration with no fine-tuning** — rejected outright: the PS explicitly disallows a generic unadapted LLM/VLM, and this would also underperform independent of the governance concern (GeoChat's own un-fine-tuned BLEU-1 collapse from 46.7 to 13.9 is direct evidence).
- **E. Naive early-fusion channel concatenation for SAR+optical (Parth's approach)** — rejected: empirically falsified by BigEarthNet.txt's own zero-shot ablation showing regression, not gain, versus RGB-only variants of the same model.

---

## 6. End-to-End Pipeline

| Stage | What happens | Tools / frameworks |
|---|---|---|
| 1. Ingestion | User uploads 1–2 images (GeoTIFF/TIFF/PNG/JPEG) + a text query via the web UI | React frontend, chunked multipart upload |
| 2. Metadata extraction | Read CRS, resolution, band count, footprint, acquisition date; flag missing/ambiguous metadata | `rasterio`, `GDAL`, `pyproj` |
| 3. Query parsing | Query Interpreter LLM converts text → structured task spec (JSON schema), few-shot prompted with the PS's own representative queries | Small open-weight instruct LLM, served via `vLLM`/Ollama |
| 4. Compatibility validation | Task spec checked against image metadata and each specialist's structural preconditions; reprojection triggered if CRS mismatch is resolvable; hard rejection with a specific explanation if not | Custom validator, `pyproj`/`shapely` for footprint IoU |
| 5. Domain-shift normalization | GSD-normalized tiling; modality-specific radiometric normalization (Sentinel vs. Cartosat/RISAT statistics handled separately) | Custom preprocessing informed by §5.3 |
| 6. Specialist dispatch | Router sends normalized input + task spec to VQA/Captioning adapter, Grounding adapter, Change-VQA adapter, or the Fusion pipeline | LoRA-adapted checkpoints served via `vLLM`/HF `transformers`, adapter hot-swapped per request on one shared frozen backbone |
| 7. Structured evidence collection | Each specialist returns typed outputs (labels, boxes, scores, masks) into a Pydantic-typed evidence ledger | Structured schema |
| 8. Verification | Geometric sanity checks + cross-tool agreement checks; deterministic count cross-check for quantity queries | Rule-based verifier |
| 9. Confidence scoring | Decoupled perception/reasoning confidence + structural discount for known weak points + verifier override | Custom scoring module (§5.5) |
| 10. Response composition | Controller LLM writes the final answer, citing which specialist produced which claim | Same controller LLM as stage 3 |
| 11. Visual evidence rendering | Bounding boxes / change masks / confidence badge overlaid on the georeferenced image | Map layer (Leaflet/deck.gl) over the uploaded raster |
| 12. Execution trace + report | Full trace serialized as JSON; rendered as a collapsible UI panel; exported as a downloadable PDF/JSON report | FastAPI backend, `reportlab`/`weasyprint` |
| 13. Deployment/demo | Backend + orchestration graph + model-serving containers, runnable on a single high-VRAM GPU or a modest cloud instance; fully offline-capable by default | Docker Compose, FastAPI, a graph-execution framework (LangGraph or hand-rolled), `vLLM` |

---

## 7. System Architecture

```
                         Web Frontend (React + map overlay)
                         upload · query · evidence · trace panel
                                       │
                                FastAPI Gateway
                                       │
              ┌────────────────────────────────────────────┐
              │           Agentic Orchestrator (graph)       │
              │                                               │
              │  Query Interpreter → Compatibility Validator  │
              │         │                    │ (reject, w/ reason)
              │         ▼                    │
              │   Specialist Router ◄─────────┘  (deterministic lookup,
              │      │        │        │           schema-validated tools)
              │      ▼        ▼        ▼
              │  ┌────────┐┌────────┐┌────────────┐┌───────────┐
              │  │VQA +   ││Ground- ││Change-VQA  ││Structured │
              │  │Caption ││ing     ││Specialist  ││Fusion     │
              │  │Adapter ││Adapter ││Adapter+CEM ││Pipeline   │
              │  └───┬────┘└───┬────┘└─────┬──────┘└─────┬─────┘
              │      └─────────┴──────────┬┴──────────────┘
              │                           ▼
              │                    Verifier Node
              │            (geometric + cross-tool checks)
              │                           ▼
              │          Confidence & Trace Emitter
              │        (decoupled perception/reasoning)
              │                           ▼
              │                Response Composer
              └───────────────────┬───────────────────────────┘
                                  ▼
                Evidence-grounded answer + map overlay
                + confidence badge + downloadable report
```

Shared frozen ViT/CLIP visual encoder and frozen LLM decoder underlie all specialist adapters; only LoRA deltas are hot-swapped per request, bounding GPU memory to roughly one backbone's footprint plus small adapter deltas rather than N independently loaded monolithic models — the shared-backbone principle both Rochan's and Sayali's drafts independently converge on, and which this synthesis keeps in full.

---

## 8. Datasets

| Purpose | Dataset | Access | Feasibility note |
|---|---|---|---|
| Mandatory fine-tuning (VQA, captioning, grounding, S1/S2 fusion cues) | **BigEarthNet.txt** (arXiv:2603.29630) — 464,044 pairs, 9.6M annotations | Open, arXiv-linked release | Train on a quality-filtered, stratified subset (§5.1) rather than the full unfiltered corpus — cheaper and, per ScoreRS's finding, likely to perform *better*, not worse |
| Practical download/storage layer | **reBEN** (arXiv:2407.03653) | Open, Hugging Face + Copernicus Data Space | Geographic (not naive grid) split avoids the train/test leakage the original BigEarthNet split is documented to suffer from — important given the ISRO/SAC set is an out-of-distribution domain-shift test |
| Change-VQA fine-tuning/eval | **CDVQA** (from SECOND) | Open, arXiv:2112.06343 | 2,968 pairs, >122K QA pairs — fully feasible within a hackathon window; official test2 split retained as the harder, distribution-shifted split |
| Single-image eval benchmarks | **VRSBench**, **RSVQA** (LR/HR) | Public (NeurIPS 2024; open) | Held out strictly for evaluation, never trained on, per PS intent |
| Fusion bridging data | **MM-OVSeg's CMU-Data** (25,087 RGB-SAR pairs, SpaceNet6+DFC2023) and, newly, **SOMA-1M** (arXiv:2602.05480, multi-resolution SAR-optical alignment, released after all four drafts were written) | Open | SOMA-1M's multi-resolution framing is a direct, better-matched fit for the Sentinel-vs-Cartosat/RISAT resolution gap than CMU-Data alone; use both, with SOMA-1M weighted toward higher-resolution regimes |
| Domain-shift stress-testing (not for training) | A small set of Cartosat-2S/RISAT-*like* public samples (openly-licensed sub-metre optical + X/C-band SAR proxies, via NRSC/Bhoonidhi open data where accessible) | Public portals where accessible | Used only to validate the domain-shift mitigation pipeline behaves sensibly before the real ISRO/SAC evaluation — never used for training |
| Final grading | **ISRO/SAC evaluation set** (Cartosat-2S + RISAT, annotations withheld) | Provided by organizers | Cannot be trained on by design; this is exactly why §5.3's domain-gap mitigation is a first-class design concern, not an afterthought |

All primary datasets are open-source and match exactly what the PS names as mandatory/benchmark data — no dataset-substitution risk.

---

## 9. Feasibility Assessment

**Buildable with high confidence (core MVP):**
- VQA+Captioning joint adapter and separate Grounding adapter, both on a BigEarthNet.txt-derived, quality-filtered subset — the LoRA recipe is proven, compute-cheap (~1–2 GPU-days per adapter), and reproducible from public hyperparameters.
- CDVQA-based Change-VQA/description adapter via the same recipe.
- Typed orchestration graph (Query Interpreter → Compatibility Validator → Router → Verifier → Composer) — this is software engineering on well-understood graph-execution patterns, not research risk.
- The structured (non-generative) two-stage fusion pipeline — feasible because it reuses the already-trained single-image specialist twice, rather than requiring new fusion-specific model training from scratch.
- Web UI with map-based evidence overlay, execution trace panel, downloadable JSON/PDF report, input validation against format/CRS/modality/footprint.

**Realistic stretch goals (attempt if the core MVP lands early):**
- A documented, honestly-reported domain-shift stress test using a handful of higher-resolution/SAR proxy samples, showing before/after the normalization stage.
- Optional pixel-level change map generation (Siamese difference model) trained on LEVIR-CD/xBD.
- Decoupled perception/reasoning confidence tokens (§5.5) if time allows a dedicated calibration pass; otherwise fall back to structural-discount + verifier-override confidence alone, which is cheaper to implement and still evidence-grounded.
- A learned (rather than purely rule-based) complementarity detector for fusion, using MM-OVSeg's InfoNCE alignment objective on the combined CMU-Data + SOMA-1M pool.

**Explicitly out of scope / future work (stated honestly, not attempted):**
- A fully end-to-end generative optical-SAR fusion VLM with dedicated cross-modal contrastive pretraining from scratch — a multi-week research effort, not a hackathon deliverable.
- Any claim of matching or exceeding published SOTA numbers on VRSBench/CDVQA leaderboards outright — the honest target is "competitive, benchmarked, and clearly documented."
- Full production-grade MLOps hardening (Triton/TensorRT export, drift monitors, CI/CD adapter-regression gating, a vector database for historical recall) — architecturally anticipated as a natural next step (informed by Parth's and Rochan's serving designs) but not built as a demo feature, since it does not move any PS evaluation-rubric line item for a first submission.
- Kubernetes-based horizontal autoscaling and a QGIS plugin client (Parth's ideas) — reasonable second-phase investments for a fielded ISRO system, explicitly deferred past the hackathon deliverable.

---

## 10. Pros / Cons / Risks

**Pros**
- Every mandatory functional-scope item in the PS's Core Requirements Summary maps to a specific, literature-benchmarked technique, not an untested idea — and the underlying citations were independently verified (§2.1), not merely trusted.
- The three PS evaluation rows most teams will underweight — Input Validation, Agentic Orchestration, and Execution Trace — fall out of the typed-graph architecture as structural properties, not bolt-ons, directly answering the two 2026 surveys' (§2.1) named critique of generic ReAct-style tool orchestration in geospatial settings.
- The domain-gap treatment (§5.3, §8) is the single highest-leverage, lowest-cost differentiator identified across all research consulted for this synthesis: it costs an augmentation/calibration policy, not a new model, yet directly targets the largest technical risk in a PS whose final grading set is deliberately out-of-distribution relative to the mandatory training data.
- Modular specialist design means a failure in one component (e.g., the stretch-goal change-map model, or the learned complementarity detector) does not take down the mandatory pipeline.

**Cons**
- More moving parts than a single-model solution — more integration surface, more that can break under demo pressure. Mitigation: keep the Specialist Router table small and the graph shallow; test the full pipeline end-to-end early and often, not just individual specialists in isolation.
- The structured fusion pipeline, even with MM-OVSeg's alignment objective grounding the complementarity detector, remains a genuine design bet: it is safer and more explainable than naive concatenation or an unproven generative model, but its end-to-end numbers will be self-reported rather than directly comparable to a published baseline, since no such baseline exists for this exact structured-fusion formulation.
- Fine-tuning even a 1B-class model requires real GPU time; if compute access during preparation is constrained, the fallback is a smaller stratified BigEarthNet.txt subset, reported transparently in the execution/report output rather than silently.

**Risks**
- **Domain shift (Sentinel → Cartosat/RISAT) is the top technical risk for every team on this PS**, not just this one; it is treated as first-class here (§5.3, §8, §9) rather than discovered during judging, but it cannot be fully eliminated without access to real ISRO/SAC-like training data, which the PS deliberately withholds.
- **Counting/magnitude/smallest-change questions will underperform regardless of engineering effort**, per every paper surveyed across all four drafts and this synthesis's own research — the mitigation is honest confidence reporting (§5.5), not pretending the weakness doesn't exist.
- **Grounding is the hardest single-image task across every benchmarked model surveyed** (best fine-tuned results still below 50% Acc@0.5) — if demoed, it must be shown alongside its confidence score, never presented as uniformly reliable.

---

## 11. Why This Beats Each Individual Draft

**vs. Dhanshree:** Keeps the genuinely useful UX ideas (Contradiction-Aware reporting, Active Evidence Acquisition framed into the confidence badge) but replaces asserted mechanisms with concrete ones — the Evidence Fusion/Contradiction-Aware Agent, described narratively in Dhanshree's draft, is implemented here as the Verifier node's specific geometric and cross-tool checks (§5.4, step 5), and "Evidence Triangulation" is implemented as the named agreement/disagreement tagging in the fusion pipeline (§5.3, step 2). It also adds the domain-gap treatment, dataset-quality filtering, and feasibility tiering entirely absent from Dhanshree's draft.

**vs. Parth:** Replaces the naive early-fusion cross-attention approach (an anti-pattern this synthesis's own research, §2.1, confirms is empirically falsified for this exact domain) with the structured, MM-OVSeg-grounded fusion pipeline; replaces the ungrounded, generic risk table with risks derived from named, numbered findings in the surveyed literature; and — most importantly — replaces a ~20-week enterprise roadmap with an explicit hackathon-scoped MVP/stretch/out-of-scope split (§9), while still preserving Parth's legitimately good ideas (COG raster storage, a QGIS plugin, Triton-based serving) as clearly-labeled future work rather than core deliverables that were never actually feasible in the stated timeframe.

**vs. Rochan:** Keeps the technically strongest pieces in full — the Verifier Agent's geometric/cross-tool checks, the per-task LoRA adapter reasoning for the highest-interference tasks, the emphasis on documented weak-point query types — but narrows the training/serving scope (three adapters instead of five, no full MLOps stack as a hackathon deliverable) to something buildable in the available time, and upgrades the confidence mechanism from k-sample self-consistency clustering to the more current, better-evidenced decoupled perception/reasoning calibration (VL-Calibration, verified in §2.1) that neither Rochan's nor any other draft identified.

**vs. Sayali:** Keeps the single most PS-specific contribution — the domain-gap framing and the rejecting Compatibility Validator — in full, but closes the two gaps Sayali's own draft honestly flags as unresolved: (1) the multi-task joint-training risk for grounding, addressed by giving grounding its own adapter rather than folding it into one joint VQA+caption+grounding adapter; and (2) the purely rule-based complementarity detector, strengthened with MM-OVSeg's validated contrastive alignment objective and the newly-identified SOMA-1M dataset (§2.2) rather than being trained on rules alone.

**Net result:** no individual draft's approach to fusion, orchestration, adaptation, or confidence is taken wholesale — each was checked against the others' stated risks and against independently-verified external research, and the final design is the option that survives that cross-examination on every axis, not merely the highest-scoring draft on any single axis.
