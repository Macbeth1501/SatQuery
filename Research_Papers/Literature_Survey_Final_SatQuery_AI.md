# Literature Survey — SatQuery AI (SIH26167)
## An Interactive Vision-Language Assistant for Multimodal Remote Sensing Image Analysis through Text Queries

**Prepared for:** ISRO / Department of Space — Smart India Hackathon, SIH26167
**Scope:** Consolidated review of ten papers covering datasets, remote-sensing vision-language models (RS-VLMs), change-VQA methods, optical–SAR fusion, and benchmark suites relevant to SatQuery AI's mandatory functional scope: single-image VQA/captioning/grounding, bi-temporal change analysis, cross-modal optical-SAR analysis, and agentic model/tool orchestration.

---

## 1. Introduction and Context

The SatQuery AI problem statement calls for an **agentic, query-driven vision-language assistant** for remote sensing (RS) that can:

1. Perform single-image tasks — VQA, captioning, and text-guided grounding.
2. Perform **cross-modal** (optical + SAR) joint analysis.
3. Perform **bi-temporal** change detection / change-VQA.
4. Orchestrate these capabilities agentically: interpreting a natural-language query, validating inputs, selecting the right specialist model(s), executing them, and returning an evidence-grounded, auditable response.

The mandatory training/fine-tuning dataset is **BigEarthNet.txt**, and the named public evaluation benchmarks are **VRSBench**, **RSVQA**, and **CDVQA**. A generic, unadapted LLM/VLM is explicitly disallowed — at least one visual or vision-language component must be fine-tuned or otherwise domain-adapted.

This survey reviews **ten papers** that collectively map onto every mandatory requirement in the problem statement:

| # | Paper | Primary Relevance to SatQuery AI |
|---|---|---|
| 1 | **BigEarthNet.txt** (Herzog et al., 2026) | The mandated training dataset — a multi-sensor (S1+S2) image-text corpus for captioning, VQA, and referring-expression detection |
| 2 | **reBEN** (Clasen et al., 2024–25) | A refined, higher-quality, practically downloadable incarnation of BigEarthNet with better labels, splits, and pretrained backbones |
| 3 | **CDVQA** (Yuan et al., 2022) | Defines the CDVQA task and dataset used as the named evaluation benchmark for multitemporal change-based VQA |
| 4 | **Revisiting Change VQA with Qwen Models** (Bazi et al., 2026) | A modern, generalist-LLM re-benchmarking of CDVQA, validating LoRA-adapted VLMs as change-VQA specialists |
| 5 | **EarthDial** (Soni et al., CVPR 2025) | A multi-sensory (RGB/SAR/MS/multi-temporal) conversational VLM — a template for the RS-adapted vision-language component |
| 6 | **GeoChat** (Kuckreja et al., CVPR 2024) | A grounded RS VLM supporting region-level captioning, referring-expression detection, and grounded conversation |
| 7 | **RS-LLaVA** (Bazi et al., 2024) | A multi-task LLaVA-derived model jointly performing captioning and VQA, with a reusable instruction-dataset-construction recipe |
| 8 | **VLMs in Remote Sensing: Progress & Trends** (Li et al., 2024, survey) | A comprehensive survey providing conceptual justification, task-by-task literature context, and a dataset/codebase directory |
| 9 | **MM-OVSeg** (Wei et al., CVPR 2025) | A multimodal Optical–SAR fusion framework for open-vocabulary segmentation — directly relevant to cross-modal analysis |
| 10 | **VRSBench** (Li et al., NeurIPS 2024) | The named public benchmark for captioning, grounding, and VQA, with a rigorous unique-vs-non-unique grounding evaluation |

Together these ten works span **datasets** (BigEarthNet.txt, reBEN, CDVQA, VRSBench), **general-purpose RS conversational VLMs** (EarthDial, GeoChat, RS-LLaVA), **change-VQA methods** (CDVQA baseline, Qwen re-benchmark), **specialized optical-SAR fusion** (MM-OVSeg), and a **field survey** (Li et al.) — covering nearly every mandatory functional block of SatQuery AI except the explicit agentic orchestration layer, which **none** of the ten papers implement. Every specialist model reviewed here is a single-purpose or monolithic system; this fragmentation is the direct empirical justification for the problem statement's demand for an *agentic* combination of specialists rather than one end-to-end model.

---

# Part A: Datasets for Remote-Sensing Adaptation

## 2. BigEarthNet.txt: A Large-Scale Multi-Sensor Image-Text Dataset and Benchmark for Earth Observation

**Authors:** Herzog, Adler, Hackel, Shu, Zavras, Papoutsis, Rota, Demir (TU Berlin / BIFOLD, U. Trento, NTUA/NOA)
**Venue:** arXiv:2603.29630 (2026)

### 2.1 Motivation and Gap Addressed

Existing RS image-text datasets suffer from two structural weaknesses that BigEarthNet.txt directly targets. Most datasets (UCM-Captions, Sydney-Captions, RSICD, RSITMD, NWPU-Captions) contain only RGB aerial imagery with short, template-like captions; even later large-scale datasets (RS5M, RSTeller, GAIA, Git-10M) remain RGB-only or provide only weak multi-sensor coverage. This is because computer-vision VLMs pretrain on RGB-only image-text data and thus have limited capability to effectively query and interpret RS data, while most RS-specific VLMs are also trained only on RGB. Existing RS image-text datasets additionally suffer from limited availability of co-registered multi-sensor data with more than three bands and limited diversity in text-annotation types, which hinders VLMs' ability to characterize both the complex spatial/spectral content of RS images and complementary information among multi-sensor data.

### 2.2 Dataset Composition

BigEarthNet.txt contains **464,044 co-registered Sentinel-1 SAR and Sentinel-2 multispectral images** with **9.6 million text annotations**, including geographically anchored captions describing land-use/land-cover (LULC) classes and their spatial relations and environmental context, VQA pairs, and referring-expression-detection instructions for bounding-box prediction. The dataset supports **15 tasks across 4 broad categories**:

1. **Captioning** — free-form descriptive text.
2. **Binary VQA** (yes/no) — Presence, Area, Counting, Adjacency.
3. **Multiple-choice VQA (MCQ)** — the four binary categories plus Relative Position, Country (Location), Season, and Climate zone.
4. **Referring expression detection** — referring LULC detection (bounding box) and referring point detection.

The co-registered S1/S2 images derive from **BigEarthNet v2.0** (549,488 pairs across ten European countries, each with a pixel-level LULC reference map based on the CLC 2018 product); after filtering images affected by snow, clouds, cloud shadows, or unclassified reference-map pixels, 464,044 co-registered pairs remain.

### 2.3 Annotation Generation Pipeline

The pipeline has three stages. **(1) Template-based caption generation**: captions are constructed by extracting four categories of spatial attributes directly from reference maps — presence of LULC classes, count of contiguous regions per class, size of each class (rounded to the nearest 1000 m²), and pairwise spatial adjacency between classes; classes are tiered as primary (>25%), secondary (5–25%), or marginal (<5%) coverage, and captions are further grounded with acquisition season, country, and Köppen-Geiger climate zone. **(2) LLM-based linguistic augmentation**: a two-stage augmentation using a quantized Llama-4-Scout-17B model first paraphrases for lexical/syntactic diversity (while prohibiting unsupported additions), then self-refines against the original template to eliminate hallucination and restore missing information; manual evaluation of ~3,200 augmented captions against four binary quality criteria yielded ~94% average correctness, with ~78% satisfying all four criteria simultaneously. **(3) VQA and referring-expression generation**: binary questions target the four spatial categories with one yes/no answer each (count/size "no" answers use an incorrect quantity; presence/adjacency "no" answers use semantically similar CLC-hierarchy classes to avoid trivial solvability); MCQs add relative-position, country, season, and climate-zone questions with one correct and three plausible incorrect options; referring LULC detection targets instances covering 1–50% of image area (≥40% within their bounding box), and referring point detection uses instance centroids. Each image pair carries up to 16 VQA pairs on average, and ~80% carry at least one referring-expression annotation.

### 2.4 Statistics and Benchmark Split

The caption annotations contain ~50 million words and 2.1 million sentences (avg. 107 words / 4.5 sentences per caption; vocabulary of 12,394 unique terms), with a bimodal length distribution corresponding to single-class vs. multi-class scenes. BigEarthNet.txt achieves an MTLD lexical-diversity score of 64.69 — more than 1.7× that of MS-CLIP (the largest prior >3-band RS dataset) — while containing ~25% more words in half as many samples.

The dataset follows the BigEarthNet v2.0 train/validation/test split (229,114 / 118,095 / 116,835 image pairs; 4,674,281 / 2,454,690 / 2,424,991 text annotations). Because LLM-augmented captions may hallucinate, a **manually curated benchmark split** of 1,082 image pairs with 15,029 text annotations — all passing manual verification on all four quality dimensions, and balanced across answer options/LULC classes — was built from the test split. It contains 6,927 binary and 5,550 MCQ VQA annotations, 970 captions, and 1,582 referring-expression annotations.

### 2.5 Benchmarking Results — Key Findings

Ten SOTA VLMs (5 CV, 5 RS) were evaluated zero-shot on the benchmark split:

| Model | Captioning (BLEU-4) | Binary VQA (Acc) | MCQ (Acc) | Ref. Exp. (mIoU) |
|---|---|---|---|---|
| GeoChat (RS) | 0.75 | 50.82 | 28.36 | 4.85 |
| EarthDial-rgb (RS) | 0.62 | 58.38 | 32.94 | 7.13 |
| EarthDial-S2 (RS) | 0.00 | 44.06 | 8.43 | 0.49 |
| EarthMind-rgb (RS) | 1.66 | 57.90 | 34.25 | 12.12 |
| EarthMind-S1S2 (RS) | 1.46 | 57.79 | 35.26 | 16.18 |
| GPT-5.2 (CV) | 0.30 | 60.39 | 34.93 | 31.73 |
| Qwen3-VL (CV) | 0.57 | 61.96 | 37.55 | 18.00 |

Key takeaways: none of the evaluated VLMs perform well overall, and CV VLMs generally outperform RS VLMs despite processing only RGB input — CV VLMs have stronger generalizability and instruction-following, whereas most RS VLMs are only suitable for tasks achievable using solely RGB. Models accepting multispectral (EarthDial-S2) or multi-sensor (EarthMind-S1S2) inputs show no consistent benefit — and sometimes decreased performance — versus their RGB counterparts, because their pretraining/fine-tuning data are largely RGB and the models were never trained to exploit the extra spectral information at inference. **This is a crucial cautionary finding: naively feeding SAR/multispectral channels into an RGB-pretrained backbone does not automatically yield gains — genuine multi-sensor fine-tuning is required.** Good performance on presence-type binary VQA mirrors scene classification (a dominant pretraining objective for RS VLMs); CV VLMs do much better at referring *point* detection than referring *LULC* detection, since a given point lets a model constrain the predicted box to a local search rather than an open-vocabulary instance search. Poor generalization to other BigEarthNet.txt tasks is attributed primarily to insufficient pretraining data rather than architectural limitation.

### 2.6 RS-InternVL: Fine-Tuning Demonstration

To isolate fine-tuning as the bottleneck, the authors adapt **InternVL3-1B** into "RS-InternVL": for each sensor modality, a pretrained ViT produces patch embeddings aligned to the InternVL LLM embedding space via linear projection layers; projected S1 and S2 tokens are concatenated with RGB tokens and the tokenized instruction before being passed to the LLM. All ViT backbones are frozen; only modality-specific projections and LoRA adapters for the LLM (rank 8, α=32, dropout 0.1) are trained — 5.8M trainable parameters out of 1.1B total. S1/S2 encoders are initialized with BigEarthNet-pretrained ViTs, using only the 10 m and 20 m S2 bands (60 m bands carry limited semantic information). Fine-tuning takes ~2 days on 4×H200 GPUs for one epoch on the combined train+validation set.

| Model | Captioning | Binary VQA | MCQ | Ref. Exp. Detection |
|---|---|---|---|---|
| Best RS specialist | 1.66 | 58.38 | 35.26 | 16.18 |
| Best CV generalist | 0.96 | 61.96 | 37.55 | 31.73 |
| **RS-InternVL (fine-tuned)** | **34.04** | **73.29** | **51.49** | **65.84** |

This is the single most important empirical result for SatQuery AI: **a small (1B-parameter), LoRA-fine-tuned, multi-sensor-adapted model trained on BigEarthNet.txt outperforms both larger general-purpose VLMs and existing RS-specialist VLMs by a wide margin** on every task category — directly validating the mandatory requirement that at least one vision/VLM component be fine-tuned on BigEarthNet.txt.

### 2.7 Implications for SatQuery AI Design

- BigEarthNet.txt's task taxonomy (presence, area, counting, adjacency, relative position, country, season, climate zone) maps almost one-to-one onto the "Single-Image VQA" and "Captioning/Grounding" mandatory scope items.
- The referring LULC/point-detection annotations map directly onto the optional "text-guided region grounding" task.
- The dataset's multi-sensor (S1+S2) co-registration format is structurally identical to the "Cross-Modal Pair" input scope (though same-time, not bi-temporal), making it a natural fine-tuning corpus for a cross-modal specialist model.
- The RS-InternVL recipe (frozen ViT + modality-specific linear projections + LoRA on the LLM) is a proven, compute-efficient blueprint the "remote-sensing-adapted vision-language component" could directly reuse.
- The finding that naive multi-sensor input without dedicated fine-tuning does not help (and can hurt) is a design warning: any cross-modal/SAR component must be explicitly trained on paired data, not simply given extra channels.

---

## 3. reBEN: Refined BigEarthNet Dataset for Remote Sensing Image Analysis

**Authors:** Clasen, Hackel, Burgert, Sumbul, Demir, Markl (TU Berlin / BIFOLD / EPFL / DFKI), 2024–2025 (arXiv:2407.03653v5)

### 3.1 Problem Addressed

The original **BigEarthNet (BEN)** family — the same dataset lineage as `BigEarthNet.txt` — has five known deficiencies that reBEN fixes: **(1) Stale atmospheric correction** — BEN's Sentinel-2 tiles used `sen2cor` v2.5.5 (2018); newer v2.11 produces materially different, higher-quality reflectance products, causing domain shift versus modern preprocessing. **(2) Label noise** — labels derive from a preliminary 2018 CORINE Land Cover (CLC) map that was later corrected but never propagated back into BEN (e.g., a "Marine waters" patch mislabeled "Urban fabric"; a patch missing a co-occurring "Urban fabric" label alongside "Pastures"). **(3) Spatially correlated train/val/test split** — BEN's grid-based split places geographically adjacent (near-duplicate, seasonally overlapping) patches in different splits, inflating reported generalization. **(4) No pixel-level annotations** — only scene-level multi-labels, precluding segmentation-style learning. **(5) Inefficient storage/format** and no modern pretrained backbones released alongside the original dataset.

### 3.2 Dataset Construction Pipeline

The same 125 Sentinel-2 L1C tiles used by original BEN (June 2017–May 2018, <1% cloud cover) were re-downloaded from the Copernicus Data Space Ecosystem and re-processed with sen2cor v2.11; 6 of 125 tiles failed radiometric/geometric QC and were excluded. Tiles are split into 1200 m × 1200 m patches (identical geographic footprint to BEN, enabling direct comparison), and each patch obtains a **pixel-level reference map** by overlaying the most recent CLC2018 (V2020_20u1) polygons — enabling both pixel- and scene-based learning. Multi-labels (19-class BigEarthNet nomenclature) are derived from these pixel maps rather than the outdated CLC map. Patches with <75% pixel-level label coverage are dropped (a validated noise/data-loss trade-off threshold); fully cloud/snow-covered patches are retained but flagged separately. Sentinel-1 SAR patches from the original BEN are re-attached, producing a final **multi-modal (S1+S2) dataset of 549,488 patch pairs**.

### 3.3 Novel Geographical Split Algorithm

Instead of a grid checkerboard split, reBEN partitions each square tile into concentric regions: an **outer frame → training set**, a **middle frame → validation set**, and an **inner core → test set**, with frame widths solved analytically to preserve BEN's approximate 2:1:1 train:val:test ratio. Because adjacent Sentinel-2 tiles overlap at their borders, assigning the outer frame to training ensures same-season overlapping patches from neighboring tiles land in the same split — eliminating the leakage that plagued BEN's grid split.

### 3.4 Supplementary Tooling

**rico-hdl** is a standalone Linux binary converting reBEN's GeoTIFF patches into an LMDB key-value store with safetensors-encoded, DL-library-agnostic tensors, removing redundant metadata and enabling high-throughput random reads for large-batch multimodal training. Public code for dataset reconstruction (`bigearthnet-pipeline`) and training scripts (`reben-training-scripts`) are released, along with pretrained weights on Hugging Face (`BIFOLD-BigEarthNetv2-0`).

### 3.5 Experimental Results

Seven backbones (ResNet-50/101, MLP-Mixer Base, MobileViT-S, MobileNet V4 Hybrid Medium, ConvNeXt V2 Base, InceptionNeXt Base, RDNet Base) were trained via ConfigILM for multi-modal multi-label scene classification (S1-only, S2-only, S1+S2 fusion). S2-only consistently beats S1-only by a wide margin (e.g., ResNet-101: 70.63% vs. 61.77% macro-AP) — optical/multispectral carries far more discriminative land-cover signal than SAR alone. **S1+S2 fusion always outperforms either single modality**, though the S1 contribution is modest once S2 is present (ResNet-101: 70.93% vs. 70.63%, +0.30 points) — SAR supplies *complementary*, not dominant, information, validating the "optical-SAR fusion" mandatory task while tempering expectations of how much lift SAR alone adds on a pure classification metric. ResNet-50/101 are the best overall performers despite being older/simpler than transformer-based options — a useful prior for picking a lightweight, fast, fine-tunable visual backbone for a resource-constrained agentic pipeline.

### 3.6 Implications for SatQuery AI Design

- reBEN is very likely the practical, download-ready, high-quality incarnation of the `BigEarthNet.txt` dataset cited as the mandatory fine-tuning corpus — it supplies co-registered S1/S2 patches exactly matching the "Cross-Modal Pair Analysis" input scope.
- The **geographical split algorithm** should be adopted (or respected) when partitioning any BigEarthNet-derived data used for the remote-sensing adaptation step, to avoid overstating generalization before facing the undisclosed ISRO/SAC evaluation set.
- The **rico-hdl / LMDB-safetensor pipeline** is directly transferable engineering for training over hundreds of thousands of paired patches, especially given the added multimodal (image+text) overhead of VLM fine-tuning.
- BigEarthNet only carries scene-level or pixel-level land-cover labels, not natural-language captions or QA pairs — it is *necessary but not sufficient* for VLM adaptation and must be paired with instruction-style datasets (RS-LLaVA's RS-instructions, VRSBench, RSVQA×BEN, etc.) for text supervision, while anchoring the *visual* representation-learning stage.
- reBEN's own patch QC pipeline (radiometric/geometric checks, cloud/snow flag, ≥75% label coverage) is a good template for the "Input Validation" component of the agentic controller — the format/modality/compatibility checks it must perform on user-uploaded GeoTIFF/TIFF images before dispatch.

---

# Part B: Multitemporal Change Detection and Change-VQA

## 4. Change Detection Meets Visual Question Answering (CDVQA)

**Authors:** Yuan, Mou, Xiong, Zhu (Technical University of Munich)
**Venue:** arXiv:2112.06343 (2022)

### 4.1 Motivation

Although change detection has great application value, its specialized nature limits change information to researchers — ordinary end users interested in a specific change in a specific region find it inconvenient to extract this from raw change maps. The paper introduces **change detection-based visual question answering (CDVQA)** on multi-temporal aerial images: given two images captured at different times and a natural-language question, CDVQA aims to answer in natural language by comparing the two images' content. This is precisely the task required by SatQuery AI's "Change-Based Visual Question Answering" mandatory scope item, and CDVQA is one of the three named public evaluation benchmarks.

### 4.2 Dataset Construction

CDVQA was created via an automatic generation method using the **SECOND** semantic change-detection dataset as source data — bi-temporal high-resolution optical (RGB) images (0.5–3 m resolution) from Shanghai, Hangzhou, Chengdu, and other Chinese cities: 4,662 pairs of 512×512 images, of which 2,968 pairs are publicly available. Each pair has pixel-level semantic change maps (7 classes: non-change plus 6 land-cover types — non-vegetated ground surface, buildings, playgrounds, water, low vegetation, trees) labeled by experts. Semantic change maps s_t1 and s_t2 assign each pixel a class 0–6; background (non-change) pixels are identical in both maps, while foreground (changed) pixels differ.

### 4.3 Question Taxonomy — Five Types

Five question types were designed: **change or not**, **increase/decrease or not**, **change to what**, **largest/smallest change**, and **change ratio** (smallest/largest change refers to the land-cover class with the least/most pixels changing). These generalize naturally to SatQuery AI's representative queries *"Has the built-up area increased, decreased, or remained unchanged?"* and *"What changed between these two dates, and where did the change occur?"*.

Generation logic: **(1) Change or not** — for an image pair, the sets of changed classes L_t1 and L_t2 are extracted; if a class belongs to either set, the answer is "yes" regardless of increase/decrease; a single-image variant asks whether change occurred specifically pre- or post-event. **(2) Increase/decrease or not** — the area of a class at T1 vs. T2 is compared; a positive delta answers "yes" to increase questions. **(3) Change to what** — a class's pixel indices in s_t1 select corresponding pixels in s_t2, and the class with the largest count among those pixels is the "major change" answer. **(4) Largest/smallest change** — the changed area per class is A_t1+A_t2, and the max/min across classes (excluding "no change") gives the answer; a single-image variant computes this per time step. **(5) Change ratio** — percentages of changed regions (overall or per class) are discretized into 11 bins (0%, 0–10%, …, 90–100%) for compatibility with a classification-based answer format. Multiple synonymous templates exist per question type, with per-type generation probabilities balancing the dataset (low probability for yes/no, high for others); on average, 16 samples are generated per image pair.

### 4.4 Dataset Statistics

More than **122,000 QA pairs** were generated from the 2,968 image pairs. Training: 65,967 QA pairs from 1,600 (53.91%) image pairs; validation: 16,441 pairs from 400 (13.48%) image pairs; the remaining 968 (32.61%) pairs generate two test sets (39,686 pairs test1; 31,036 pairs test2, with overlap) to evaluate robustness under different answer distributions. Answer distributions are long-tailed ("no" dominates at 30.9%/31.15% of train/test1 answers; some ratio buckets occupy only ~0.22% of samples); test2 skews toward harder question types (change to what, change ratio, class change ratio), making it the more difficult split. There are **19 total answer classes**: {no, yes, 10 ratio bins, 7 land-cover class names}.

### 4.5 Baseline CDVQA Architecture

Four parts: multi-temporal feature encoding, multi-temporal fusion, multi-modal fusion, and answer prediction, plus a **Change Enhancing Module (CEM)**. The multi-temporal encoder is a Siamese-style network (F1=f1(x_t1), F2=f2(x_t2), sharing architecture/parameters); both CNN backbones (ResNet-18/101/152) and a ViT-based Transformer encoder were studied. The CEM treats F1 and F2 as query/key (analogous to self-attention), computing similarity F_s=|f_q(F1)−f_k(F2)| via 1×1 convolutions; a change-enhancing map M_ce=σ(f_c(F_s)) is obtained, scaled by a learnable parameter θ (initialized to 0), added to an identity matrix, and multiplied elementwise with F1/F2 to produce enhanced features — encouraging the model to focus on regions of large temporal difference. Fusion strategies compared: element-wise subtraction, normalized subtraction, concatenation, summation, and multiplication. A pretrained skip-thoughts encoder produces the question feature vector; the visual feature is projected and concatenated with the question vector, then passed through two fully connected layers (256-dim, then 19 classes) for classification-style answer prediction.

### 4.6 Key Experimental Findings

Compared to ResNet-18/101, ResNet-152 shows no significant advantage; a ViT-based Transformer encoder does further improve performance (self-attention benefits representative feature learning), but overall, backbone choice has very little impact — suggesting visual feature learning is *not* the key bottleneck; multi-temporal fusion and change analysis are more critical. **Concatenation performs best** among the five fusion operations (more flexible, learnable-weight fusion via FC layers); subtraction (even L2-normalized) does *not* outperform concatenation/summation, indicating a dedicated change-analysis module is needed rather than naive differencing. The **CEM consistently improves** average and overall accuracy on both test sets (e.g., test1 average accuracy: 0.5766 → 0.6008 with CEM; overall: 0.6763 → 0.6903). Cross-dataset generalization (138 manually annotated HTCD pairs, 3,303 QA pairs) shows a CDVQA-trained model achieves 0.1969 average accuracy vs. 0.0601 for random initialization — better than chance but far from satisfactory, indicating a real domain gap. The paper concludes CDVQA is complex because a model must both learn multi-modal representations *and* analyze semantic change (locating changed areas *and* identifying their land-cover classes); since the baseline doesn't use semantic change labels directly, land-cover-class-related questions are comparatively weaker.

### 4.7 Implications for SatQuery AI Design

- CDVQA is a named public evaluation benchmark; its five-way question taxonomy provides a ready-made structure for a "change-understanding" or "change-VQA" specialist tool.
- The failure of naive subtraction-based fusion and the success of a dedicated **change-enhancing attention module** argues that SatQuery AI's change-detection specialist should include an explicit difference-attention mechanism.
- The 19-class closed-vocabulary answer format is well suited to classification-style change-VQA but is limited compared to open-ended answering; SatQuery AI's specialist should ideally generate open natural-language answers while remaining checkable against this closed taxonomy for evaluation.
- The poor cross-dataset transfer result cautions that a change-VQA specialist tuned only on one bi-temporal dataset may not directly generalize to ISRO's Cartosat/RISAT pairs without further domain adaptation.
- Backbone scale mattering far less than fusion/attention design supports using compact backbones (echoed by RS-InternVL) provided the fusion mechanism is well designed — a compute-efficient strategy for a hackathon-timeline deliverable.

---

## 5. Revisiting Change VQA in Remote Sensing with Structured and Native Multimodal Qwen Models

**Authors:** Bazi, Al Rahhal, Zuair, Mohamed (King Saud University), 2026 (arXiv:2604.18429v1)

### 5.1 Problem Addressed

Change VQA has historically used bespoke, task-specific architectures (e.g., the CDVQA baseline above). This paper asks whether modern **generalist** multimodal LLMs (the Qwen family) can handle Change VQA competitively **without hand-crafted change-detection modules**, contrasting two integration philosophies: **Qwen3-VL** — a *structured* pipeline (shared ViT → PatchMerger → **DeepStack** ×3 injecting visual features at multiple decoder depths → full self-attention decoder) — versus **Qwen3.5** — a more *natively* multimodal design (same ViT/PatchMerger front end, no DeepStack; single-stage alignment feeding a hybrid decoder combining GatedDeltaNet linear-attention-like layers with full-attention layers).

### 5.2 Problem Formulation

Given a bi-temporal pair (I⁽¹⁾, I⁽²⁾) and question q, Change VQA is a closed-set classification problem, but training is framed as **autoregressive generation** (next-token prediction over the answer sequence), with generation constrained to the valid answer vocabulary at inference — the same generative-LLM formulation SatQuery AI needs for open-ended, natural-language change-VQA responses while remaining scoreable against CDVQA's closed answer set.

### 5.3 Adaptation Method

Both models are adapted via **LoRA** (r=16, α=32) applied only to the decoder's Q/K/V/O attention projections; the vision encoder and visual-alignment modules (PatchMerger, DeepStack) remain frozen. Because Qwen3-VL is full-attention throughout while Qwen3.5 mixes in cheaper GatedDeltaNet layers, LoRA touches more parameters (percentage-wise) in Qwen3-VL, but overall trainable-parameter counts remain a small fraction (0.3–0.8%) of total model size across scales 0.8B–9B. Training uses LLaMA-Factory, batch size 32, 3 epochs, LR 5×10⁻⁵, bfloat16.

### 5.4 Dataset — CDVQA

The same CDVQA dataset (from SECOND): 2,968 bi-temporal pairs, >122,000 QA pairs across eight reasoning types (change ratio, class change ratio, change or not, change to what, increase or not, decrease or not, smallest change, largest change), six land-cover answer classes. Splits: 65,967/1,600 (train), 16,441/400 (val), test1 (39,686 QA) and test2 (31,036 QA).

### 5.5 Results

**Qwen3.5 generally outperforms Qwen3-VL at comparable scale**, especially on test2 (2B variant: OA 65.38 → 70.94 going from Qwen3-VL-2B to Qwen3.5-2B). **Scaling is non-monotonic**: within each family, the largest model (8B/9B) does not always beat the mid-size (2B/4B) variant — Qwen3-VL-8B underperforms Qwen3-VL-4B on both test splits, suggesting diminishing/negative returns from naive up-scaling under LoRA with a fixed rank. **Qwen3.5-2B is the best accuracy/efficiency trade-off overall.** Per-question-type breakdown: binary/directional questions (change or not, increase/decrease) are stable and high-accuracy (~80–85%) across all variants, whereas fine-grained ranking under subtle change (smallest change) or quantitative discretization (change ratio) remain the hardest categories (30–60% accuracy) and dominate residual error. Compared to prior specialized methods (CDVQA baseline, SOBA, VisTA), **Qwen3.5-2B — a compact, general-purpose multimodal model with only LoRA adaptation — outperforms all of them** on both AA and OA across test1/test2. Qualitative failure analysis shows three recurring error modes: false positives on subtle/negative changes; confusing the smallest semantic change among visually similar candidate categories; predicting an adjacent-but-wrong discretized change-ratio bucket.

### 5.6 Implications for SatQuery AI Design

- Directly validates the feasibility of a "Change-VQA model" specialist tool, and supplies a concrete, benchmarked recipe (Qwen3.5 backbone + LoRA on attention projections, frozen vision tower) that could be replicated.
- Confirms **CDVQA is the correct benchmark** for Change-VQA numbers, and gives concrete baseline numbers (VisTA: ~65.9/73.1 AA/OA on test1) a competitive submission should aim to match or exceed.
- Native, tightly-integrated multimodal decoders (hybrid linear+full attention) beat structured multi-depth-conditioned pipelines for change reasoning — an architecture-selection signal favoring models with strong cross-image token interaction.
- The LoRA-only, frozen-encoder strategy is compute-efficient and directly satisfies the "Remote-Sensing Adaptation" mandatory requirement without full-model retraining.
- The identified weak spots (fine-grained magnitude/ratio estimation, smallest-change discrimination) should inform the confidence-estimation component: the controller should flag lower confidence specifically for "how much changed" and "which change is smallest" query types.
- Because this is a bi-temporal, single-modality (optical/aerial) benchmark, it validates the multitemporal-VQA half of SatQuery AI's scope but not the optical-SAR cross-modal requirement, which must be sourced from BigEarthNet/reBEN or a dedicated fusion dataset (see §9, MM-OVSeg).

---

# Part C: Remote-Sensing Vision-Language Models

## 6. EarthDial: Turning Multi-sensory Earth Observations to Interactive Dialogues

**Authors:** Soni, Dudhane, Debary, Fiaz, Munir, Danish, Fraccaro, Watson, Klein, Khan, Khan (IBM Research, MBZUAI, ANU, Linköping)
**Venue:** CVPR 2025

### 6.1 Motivation and Positioning

Existing generic VLMs do not scale well to Earth Observation (EO) data — even state-of-the-art proprietary models like GPT-4V show low accuracies on domain-specific RS data, emphasizing the need for EO-specialized VLMs. EarthDial is introduced as a conversational assistant transforming complex multi-sensory Earth observations into interactive natural-language dialogues, supporting multi-spectral, multi-temporal, and multi-resolution imagery, and enabling classification, detection, captioning, question answering, visual reasoning, and visual grounding. Prior RS-specific VLMs (GeoChat, LHRS-Bot, SkyEyeGPT) are limited in high-resolution processing and lack multi-spectral/multi-temporal analysis; EarthGPT integrates optical/SAR/infrared but not other multispectral inputs and lacks generalization to multi-temporal/varying-resolution inputs.

### 6.2 Dataset: EarthDial-Instruct

EarthDial introduces an instruction-tuning dataset of over **11.11M instruction pairs** covering RGB imagery at varying resolutions, SAR, and multispectral modalities (NIR, infrared), handling bi-temporal and multi-temporal sequences for change detection and temporal scene classification. It is the first dataset simultaneously covering open-source availability, multi-spectral, multi-temporal, and multi-resolution imagery, with the widest task coverage across sixteen task types, and is 6× larger than prior RS-VLM datasets. Construction pipeline: pretraining QA pairs are curated from SkyScript and SatlasPretrain data (S2/S1/NAIP/Landsat with labels) using InternLM-XComposer2 to generate instructions from labels, filtering sparse-label samples and applying luminance/coverage-based cloud filtering. Downstream task datasets span ten task types and six visual modalities (Optical, SAR, S2, Infrared, NIR, Hyperspectral) plus two temporal modalities — including scene classification (BigEarthNet multi-label, FMoW temporal), object detection with refer/identify/grounding tags across optical/SAR/infrared, change detection (three binary datasets + MUDS multitemporal, with manually generated captions for MUDS), methane-plume detection (STARCOP), urban heat island (LST/NDVI from S2/Landsat), and disaster assessment (xBD bi-temporal, QuakeSet bi-temporal SAR).

### 6.3 Model Architecture

Three trainable components — a visual encoder, an MLP layer projector, and an LLM — built on InternVL with modifications for multi-spectral/multi-temporal processing. The model is lightweight (4B parameters), using InternViT-300M (distilled from a larger 6B InternViT) and Phi-3-mini, connected via an MLP projector. Two novel modules: **Adaptive High Resolution** dynamically selects an optimal aspect ratio, dividing the image into 448×448 tiles plus a thumbnail for global context (1–12 tiles during training, up to 40 at inference); **Data Fusion** iteratively processes three channels at a time through the ViT, aggregating via bilinear interpolation (AnyRes block) for multi-spectral inputs, with reduced visual embeddings concatenated with text embeddings before the LLM (RGB temporal images pass through the ViT separately, then tokens are stacked and concatenated).

### 6.4 Three-Stage Training Strategy

**Stage 1 (RS Conversational Pretraining)** trains all learnable components on Satlas/SkyScript (7.6M pairs) with a simple architecture (no fusion, no temporal/multispectral) to first establish strong single-image RGB representations. **Stage 2 (RGB and Temporal fine-tuning)** fine-tunes only MLP+LLM (ViT frozen) on captioning, classification, detection, VQA, and temporal change detection, applying data fusion for multi-temporal inputs. **Stage 3 (Multispectral and SAR fine-tuning)** extends to multispectral RGBI and SAR by introducing the data fusion module while keeping ViT frozen from Stage 1, fine-tuning only MLP and LLM layers.

### 6.5 Benchmark Results

| Model | AID (RGB) | UCMerced (RGB) | WHU-19 (RGB) | BigEarthNet (RGB) | xBD Set1 (Temporal) | fMoW (Temporal) |
|---|---|---|---|---|---|---|
| GPT-4o | 74.73 | 88.76 | 91.14 | 49 | 67.95 | 21.43 |
| InternVL-8B | 60.4 | 58.23 | 79.3 | 19.73 | 51.44 | 21.04 |
| GeoChat | 72.03 | 84.43 | 80.09 | 20.35 | 53.32 | 59.2 |
| **EarthDial** | **88.76** | **92.42** | **96.21** | **68.82** | **96.37** | **70.03** |

EarthDial shows significant improvement over generic and specialized VLMs, with consistent gains on multi-spectral datasets and RGB-Infrared TreeSatAI, and strong FMoW/xBD results. For MS modality, EarthDial achieves an average **32.5%** improvement in classification accuracy over GPT-4o; for RGBI, **40.2%** higher accuracy; a similar trend holds for SAR object detection (higher mAP@0.5). On change-detection captioning (Dubai CC, LEVIR-MCI, MUDS, SYSU), EarthDial substantially outperforms GPT-4o/InternVL2-4B/GeoChat (e.g., MUDS ROUGE-1: EarthDial 28.16 vs. GeoChat 12.28 vs. GPT-4o 14.18). On xBD disaster assessment, EarthDial outperforms all VLMs across captioning, region/image classification, detection, and referred-object detection; on QuakeSet (SAR earthquake prediction), EarthDial reaches 57.53% vs. 55.86% for GPT-4o. On urban-heat-island (Landsat-8) and STARCOP methane-plume classification, EarthDial reaches 56.77%/77.09% versus GPT-4o's 22.68%/40.93%.

Ablations show multi-stage pretraining improves referred-object-detection mAP@0.5 by 5 points; for multi-spectral band fusion, bilinear interpolation beats average pooling by 13.5% (BigEarthNet MS: 67.01% vs. 47.66% vs. 34.62% max-pooling), and multi-spectral fusion yields a further 1.75% improvement over the RGB-only counterpart.

### 6.6 Implications for SatQuery AI Design

- EarthDial is the closest existing analogue to a unified "remote-sensing-adapted vision-language component," but it is a **single monolithic conversational model**, not an agentic orchestrator of multiple specialist tools — demonstrating what a fine-tuned multi-sensor VLM can achieve, but not the query-interpretation → task-classification → tool-selection → execution pipeline SatQuery AI mandates.
- Its three-stage training recipe (RGB pretraining → RGB/temporal fine-tuning → multispectral/SAR fine-tuning) is a strong template for progressively adapting a core VLM backbone under compute constraints.
- The **Adaptive High Resolution** and **Data Fusion** modules are directly reusable for handling GeoTIFF/high-resolution and multi-band optical-SAR inputs.
- Strong disaster-assessment/change-detection results provide evidence that a properly adapted VLM backbone can serve as the "change-understanding" specialist, given similar bi-temporal instruction data.
- The advantage of a lightweight 4B model over GPT-4o/InternVL-8B reinforces that domain adaptation matters far more than raw parameter count.
- EarthDial does not report **cross-modal joint reasoning outputs** (a fused textual answer explicitly referencing both optical and SAR evidence) — this remains a gap that the agentic controller, or a dedicated fusion specialist (MM-OVSeg, §9), must fill.

---

## 7. GeoChat: Grounded Large Vision-Language Model for Remote Sensing

**Authors:** Kuckreja, Danish, Naseer, Das, Khan, Khan (MBZUAI, BITS Hyderabad, ANU, Linköping)
**Venue:** CVPR 2024

### 7.1 Motivation

General-domain VLMs designed for natural images perform poorly on RS imagery, because the content of RS image-text pairs differs substantially from web data, causing hallucination and inaccuracy. Prior RS VQA methods framed the task as closed-set classification (choosing from predetermined training responses), limiting open-ended answer generation and instruction-following. GeoChat extends multimodal instruction-tuning to RS, training a multitask conversational assistant with an automated pipeline generating ~318k RS multimodal instructions drawn from LR-BEN (VQA), NWPU-RESISC-45 (scene classification), and SAMRS (object detection).

### 7.2 Task Taxonomy — Three Levels of Granularity

GeoChat formally supports: **(a) Image-Level Conversation** — processing an image/query without spatial coordinates, for VQA, scene classification, and holistic captioning; **(b) Region-Level Conversation** — spatial box locations plus image/query, for region-level captioning, region-specific VQA, or multi-turn conversation; **(c) Grounded Conversation** — special task-specification tokens providing object locations at different granularities while maintaining conversational ability, covering grounded captioning/conversation, object grounding, and referring-expression detection. This maps closely onto SatQuery AI's scope: image-level tasks ↔ single-image VQA/captioning; grounded conversation ↔ text-guided region grounding.

### 7.3 Architecture

Follows LLaVA-v1.5: a Global Image encoder, an MLP adaptor (two linear layers), and an LLM, with an added task-prompt token indicating the desired task (grounding, image-level, region-level), plus support for spatial positions in both inputs and outputs. Three task identities t ∈ {grounding, identify, refer} are used for grounded conversations, region captioning, and referring-expression comprehension respectively; VQA/scene classification need no task token. Box locations use a textual format b = {b_x_left, b_y_top, b_x_right, b_y_bottom | θ}, normalized within [0,100], with θ as a rotation angle. The visual backbone adapts CLIP-ViT(L-14) — natively 336×336 (576 patches) — with interpolated positional encoding supporting 504×504 (~1,296 patches, nearly double) for better grounding of small objects. The LLM is Vicuna-v1.5 (7B), fine-tuned via LoRA (two smaller matrices approximating the original weight matrix), preserving generic knowledge while adapting to RS.

### 7.4 Instruction Dataset Construction (318k pairs)

Three dataset types integrated: object detection (DOTA, DIOR, FAIR1M → SAMRS), scene classification (NWPU-RESISC-45), and VQA (LRBEN + Floodnet flood-detection VQA); detection datasets provide masks alongside boxes for region-level reasoning. Missing classes (buildings, roads, trees) are filled via ViTAE-RVSA pseudo-labels (pretrained on LoveDA), with predictions overlapping SAMRS ground truth removed to reduce noise. Five attribute types are derived per object for referring expressions: category, color (K-Means clustering, largest cluster's center), relative size (20th/80th percentile thresholds), relative location (3×3 grid), and relation (distance-based sub-graph grouping + pixel-level containment checks, e.g., "surrounded by"). Predefined textual templates encode these into single-object and pairwise-relation expressions. Vicuna is then prompted with few-shot examples to generate multi-round QA "as if it could visualize the image" from caption/attribute text alone — 65k images → multi-round conversations, 10k → complex QAs, 30k → detailed descriptions, yielding ~308k training + 10k testing image-instruction pairs.

### 7.5 Benchmark Results

**Zero-shot scene classification:**

| Model | UCMerced | AID |
|---|---|---|
| Qwen-VL | 62.90 | 52.60 |
| MiniGPTv2 | 4.76 | 12.90 |
| LLaVA-1.5 | 68.00 | 51.00 |
| **GeoChat** | **84.43** | **72.03** |

GeoChat significantly outperforms other VLMs; MiniGPT-4-v2 notably fails to follow classification instructions (near-5% self-checked accuracy); Qwen-VL/LLaVA-1.5 follow instructions well but lack domain knowledge. On RSVQA-LRBEN, GeoChat performs close to SOTA specialists (notably RSGPT); on RSVQA-HRBEN it outperforms other zero-shot VLMs by 3.9% average accuracy, beating LLaVA-v1.5 by 15.9% on the Comparison subset. On its own visual-grounding benchmark (7,593 [refer], 560 [grounding], 495 grounding-description, 2,793 region-captioning questions at Acc@0.5 IoU), performance is low on small objects or multi-box predictions; GeoChat beats MiniGPT-4-v2 on medium-size images and on grounding-description (both text answer and box IoU) and significantly outperforms it in ROUGE/METEOR for region-level captioning.

### 7.6 Implications for SatQuery AI Design

- GeoChat's **task-token mechanism** (`[grounding]`, `[identify]`, `[refer]` prepended to the prompt) is directly analogous to the explicit task-routing signal the agentic controller needs to send to specialist sub-models — a single backbone can serve multiple task types when explicitly told which task to perform.
- The **textual bounding-box representation** `{x_left, y_top, x_right, y_bottom | θ}` with rotation angle and [0,100] normalization is a clean, LLM-native format for "visual evidence" and "spatial change map" outputs, directly adoptable as a grounding output schema.
- The attribute-extraction pipeline (color via K-means, relative size via percentile thresholds, relative position via 3×3 grid, relations via distance-graph + containment check) is a reusable recipe for generating referring-expression/grounding training data from any RS object-detection dataset with bounding boxes.
- GeoChat is explicitly a **single-image** specialist with no multi-temporal or multi-sensor (SAR) capability — complementary to, not a replacement for, the change-detection and cross-modal fusion specialists SatQuery AI requires.
- The LoRA-based fine-tuning strategy (freezing MLP adaptor and CLIP encoder; adapting only LLM attention weights W_q, W_v at rank 64) offers a second proven compute-efficient adaptation recipe alongside RS-InternVL's approach.

---

## 8. RS-LLaVA: A Large Vision-Language Model for Joint Captioning and Question Answering in Remote Sensing Imagery

**Authors:** Bazi, Bashmal, Al Rahhal, Ricci, Melgani, *Remote Sensing* 2024, 16(9):1477

### 8.1 Problem Addressed

Prior RS vision-language work trains separate single-task models per dataset/task (captioning *or* VQA), ignoring shared structure and wasting scarce RS-labeled data. RS-LLaVA proposes a **single multi-task LVLM**, adapted from LLaVA, jointly performing captioning and VQA from one set of weights — motivated by efficiency, reduced overfitting risk on small RS datasets, and better UX. This is essentially a miniature precursor to the "single agentic assistant, many specialist behaviors" philosophy that SatQuery AI scales up with an explicit tool-routing controller.

### 8.2 The RS-Instructions Dataset

No unified RS instruction-tuning dataset existed, so the authors reformatted four existing single-task datasets into instruction/response pairs:

| Dataset | Task | #Images | Size | Resolution |
|---|---|---|---|---|
| UCM-captions | Captioning | 2,100 | 256×256 | 0.3048 m |
| UAV | Captioning | 2,628 | 256×256 | 0.02 m |
| RSVQA-LR | VQA | 772 | 256×256 | 10 m |
| RSIVQA-DOTA | VQA | 1,868 | varies | varies |

Combined into **7,058 samples** (5,506 train / 1,552 test); VQA datasets are cast as multi-turn Human/GPT conversations, while captioning datasets pair paraphrased instruction templates with ground-truth captions — a reusable template for synthesizing a multi-task instruction corpus by wrapping VRSBench/RSVQA/CDVQA ground truth into instruction-response format.

### 8.3 Architecture and Training

Frozen CLIP-ViT-Large @336×336 visual backbone; a 2-layer MLP with GELU projects visual tokens into the LLM's embedding space; Vicuna-v1.5 (7B and 13B), likewise mostly frozen. Two-stage training: (1) pretrain only the projection layer on a general image-text corpus for modality alignment; (2) **LoRA fine-tune** the LLM (applied to W_q, W_k, W_v) on RS-instructions, keeping vision encoder and base LLM frozen — reinforcing LoRA as the de facto efficient adaptation approach across the survey. LoRA rank 64, α=16, Adam LR 1×10⁻⁴.

### 8.4 Results

Joint (multi-task) vs. single-task training: on UCM-captions, joint training gives a small but real improvement for the 7B model and a larger gain for 13B; on the small UAV dataset (~2,600 crops), single-task fine-tuning beats joint training, and the smaller 7B model beats 13B — multi-task learning helps most when data diversity is sufficient, but can dilute performance on very small, narrow datasets. On RSVQA-LR, single-dataset fine-tuning modestly outperforms joint training (88.56% vs. 88.13% average accuracy for 7B). On RSIVQA-DOTA, the joint 7B model gets the best-balanced precision/recall and lowest counting RMSE, while the joint 13B model catastrophically collapses on presence detection (F1 drops to 49.94) — larger LLM backbones are not uniformly better under multi-task LoRA adaptation, and per-task validation is essential. RS-LLaVA (13B, joint) beats all prior specialized captioning/VQA methods on UCM-captions, UAV, and RSVQA-LR in nearly every metric. Qualitative results show the model handles presence/description well but struggles specifically with **counting** — a known broad weak point directly relevant since SatQuery AI's representative queries include implicit counting/estimation tasks.

### 8.5 Implications for SatQuery AI Design

- RS-LLaVA is close to a minimum-viable version of the single-image VQA + captioning half of SatQuery AI's mandatory scope; the frozen-encoder + LoRA-on-LLM recipe, validated across multiple papers, should be the default remote-sensing-adaptation strategy for the core VLM component.
- The RS-instructions construction methodology (converting existing labeled datasets into Human/GPT instruction turns) is directly reusable for building a unified multi-task instruction set combining BigEarthNet-derived captions/labels with VRSBench, RSVQA, and CDVQA-style QA pairs.
- Joint multi-task training helping or hurting depending on dataset size/diversity suggests running **separate specialist LoRA adapters** per task (VQA, captioning, grounding, change-VQA, fusion) on a shared frozen backbone — exactly what the problem statement's "multiple specialised components" suggests — sidestepping task interference while the agentic controller supplies the "single assistant" UX.
- The persistent counting weakness reinforces flagging lower confidence on quantity-related queries regardless of which specialist answers them.
- Confirms CLIP-ViT + Vicuna/LLaVA-style backbones with LoRA as a mature, well-validated "remote-sensing-adapted vision-language component."

---

## 9. Vision-Language Models in Remote Sensing: Current Progress and Future Trends

**Authors:** Li, Wen, Hu, Yuan, Zhu, *IEEE Geoscience and Remote Sensing Magazine*, 2024 (arXiv:2305.05726v2)

### 9.1 Scope

A comprehensive survey (not a novel method paper) covering the evolution from vision-centric models → LLMs → VLMs, and their application across seven RS tasks: image captioning, text-to-image generation, text-based image retrieval, VQA, scene classification, semantic segmentation, and object detection. This is the single most useful reference document for grounding SatQuery AI's design in the broader literature landscape, and doubles as a dataset/codebase directory.

### 9.2 Background Concepts Covered

**Vision-centric foundation models** (RingMo, plain ViT-based models, GFM, billion-scale RS foundation models) trained via supervised or self-supervised (contrastive, masked-image-modeling) pretraining on large unlabeled RS corpora (MillionAID, GeoPile) are relevant as candidate pretrained visual backbones beyond generic CLIP. The taxonomy of **fusion-encoder vs. dual-encoder VLM architectures** — VisualBERT/UNITER/OSCAR (single-stream fusion) vs. ViLBERT/LXMERT (dual-stream co-attention) vs. CLIP/ALIGN (dual encoder, contrastive, no cross-attention, efficient for retrieval) — clarifies why CLIP is the default choice for RS text-image retrieval and zero-shot classification, while LLaVA-style single-stream fusion is preferred for generative captioning/VQA. This is a design fork SatQuery AI must face explicitly: a lightweight CLIP-based tool for coarse retrieval/gating vs. a heavier generative VLM for detailed answers.

### 9.3 Task-by-Task Survey (highlights)

**Captioning**: traces CNN+RNN encoder-decoders through attention-based models to transformer/LLM-based captioners; **RSGPT** (Q-Former + frozen LLM) achieves SOTA on UCM-caption/Sydney-caption/RSICD, and its RSICap dataset (2,585 human-annotated captions) is high-quality but too small to train large VLMs from scratch — directly foreshadowing why VRSBench (§10) was created at larger scale. **VQA**: comprehensive history — RSVQA (Lobry et al., the pioneering closed-set benchmark named in the problem statement), RSIVQA, VQA-TextRS (open-ended), Bi-Modal Transformer (CLIP-based), and CDVQA (Yuan et al.) — identified as the first work to frame change detection as VQA, giving historical/architectural context (multitemporal encoding → multitemporal fusion → multimodal fusion → answer prediction, a template SatQuery AI's Change-VQA specialist could mirror). RSGPT again achieves best overall performance on RSVQA-HR/LR. **Visual Grounding**: RSVG and DIOR-RSVG (17,402 images/38,320 expressions) datasets; the survey explicitly cautions that RSVG performance still trails conventional object detection and needs RS-specific adaptation (multi-scale features, multi-granularity language, noise filtering) — flagging grounding as a harder, less mature capability than VQA/captioning. **Zero-Shot Scene Classification / Few-Shot Detection**: RS-CLIP (curriculum-learning pseudo-labeling) achieves dramatic accuracy jumps over earlier semantic-embedding approaches — outside mandatory scope but informative if the specialist registry is extended.

### 9.4 Resource Directory

Compiles: a large table of RS vision-language datasets spanning scene classification, captioning, VQA, grounding, detection, segmentation — including RSVQA, RSIVQA, CDVQA, RSVG, DIOR-RSVG, BigEarthNet; open-source codebases (Huggingface Transformers, MiniGPT-4/v2, LLaVA, Qwen-VL, Shikra); and other tools (OpenAI API, LAVIS, Midjourney for synthetic data).

### 9.5 Identified Limitations & Future Directions

RS training datasets remain orders of magnitude smaller than web-scale corpora; most existing RS-VLMs still rely on classical CNN/RNN rather than modern ViT/LLM backbones; training billion-parameter models from scratch is compute-prohibitive, motivating **efficient fine-tuning** — prompt tuning, adapters, and **LoRA are explicitly recommended** ("can reduce trainable parameters by 10,000× and GPU memory by 3×"); RS data variability (lighting, atmosphere, sensor noise) is under-modeled; large spatiotemporal scale is a poorly addressed challenge; and the survey calls for unified VLMs across many RS tasks, naming RSGPT and GeoChat as pioneering steps.

### 9.6 Implications for SatQuery AI Design

- Provides the conceptual justification for nearly every mandatory design decision: why RS-specific fine-tuning is required, why LoRA/efficient fine-tuning is the right adaptation strategy (explicitly recommended and empirically validated elsewhere in this survey), and why an agentic, multi-specialist architecture is preferable to a single monolithic VLM.
- Confirms RSVQA and CDVQA as historically canonical, most-cited benchmarks for single-image VQA and change-VQA respectively, validating the problem statement's choice of these two benchmarks (plus VRSBench).
- The caution that grounding trails object detection in maturity should inform risk planning: since "text-guided region grounding" is only one of two options for the additional single-image task (the other being captioning), **captioning is the lower-risk mandatory-adjacent deliverable**, with grounding as a stretch goal.
- Flags GeoChat as the most advanced unified system in the literature — VRSBench (§10) subsequently benchmarks it directly, making it the single most important existing off-the-shelf candidate backbone.
- The dataset table gives a ready-made shortlist of open-source datasets beyond the three named in the problem statement (RSICD, RSITMD, RSVG, DIOR-RSVG, Sydney-captions) that could supplement training data without violating the "open-source datasets only" constraint.

---

# Part D: Optical–SAR Fusion and Multi-Task Benchmarks

## 10. MM-OVSeg: Multimodal Optical–SAR Fusion for Open-Vocabulary Segmentation in Remote Sensing

**Authors:** Wei, Xiao, Chen, Xia, Yokoya (University of Tokyo, RIKEN AIP)
**Venue:** CVPR 2025

### 10.1 Motivation

Open-vocabulary segmentation (OVS) enables pixel-level recognition from an open set of textual categories, but progress remains largely limited to clear-sky optical data and struggles under cloudy/haze-contaminated conditions — a serious limitation for time-sensitive applications such as disaster response and for consistent long-term monitoring. Optical images provide rich spectral and semantic cues while SAR penetrates clouds and captures structural information, enabling robust scene understanding under adverse weather — directly targeting the problem statement's rationale for optical-SAR fusion.

### 10.2 Two Core Technical Challenges

Integrating SAR into an open-vocabulary framework presents two obstacles: vision foundation models (VFMs) are primarily trained on RGB imagery, whereas SAR exhibits distinct backscattering properties and texture patterns, creating a substantial domain gap; and vision-language models such as CLIP/ALIGN are trained with image-level supervision, limiting their capacity for accurate dense (pixel-level) predictions — an issue exacerbated for SAR where domain discrepancies further weaken spatial correspondence between visual and textual representations.

### 10.3 Architecture — Two-Stage Framework

MM-OVSeg's design directly parallels a "cross-modal information-extraction specialist" as named in SatQuery AI's agentic-tool registry. **Stage 1 — Cross-Modal Unification (CMU)**: DINO is used as the dense-feature backbone; because DINO does not directly generalize to SAR and collecting a SAR corpus at DINO's RGB-training scale is unrealistic, SAR and RGB embeddings are unified using unlabeled, co-registered RGB-SAR pairs (inspired by ImageBind). Each RGB image is encoded by a frozen RGB DINO encoder to obtain f_rgb, while its SAR counterpart is processed by a learnable SAR encoder to produce f_sar; cross-modal alignment is optimized via an InfoNCE contrastive loss unsupervised, with both encoders using a ViT-B/16 backbone and multi-scale features from the 4th, 8th, and 12th transformer blocks. A dataset of 25,087 aligned RGB-SAR pairs (**CMU-Data**, from SpaceNet6 and DFC2023, 0.5–3 m resolution) is curated for this. Notably, the authors find it unnecessary to also train a CLIP-style visual encoder for SAR, because the pretrained CLIP visual encoder captures global semantic cues (scene layout, object co-occurrence, contextual relations) that remain largely invariant across optical and SAR modalities — a useful design economy: only the *dense local* (DINO) encoder needs cross-modal adaptation; the *global semantic* (CLIP) encoder can remain RGB-only.

**Stage 2 — Dual-Encoder Fusion (DEF)**: the pretrained RGB DINO encoder and the CMU-aligned SAR DINO encoder are frozen, while CLIP visual/text encoders remain trainable; DEF integrates CLIP and DINO to extract complementary RGB-SAR cues aligned with textual semantics. Dense features from the 4th/8th/12th ViT-B/16 blocks (both RGB and SAR) are projected to a unified dimension and fused via element-wise addition. CLIP produces global visual/textual embeddings using the prompt "a photo of {CLASSLIST}"; dense and global visual-text similarities are computed via cosine similarity, transformed by a 7×7 convolution and sigmoid, then fused via concatenation and residual enhancement (the residual connection preserving CLIP's generalist semantic structure). An FPN-style decoder upsamples and concatenates fused features with corresponding DINO/CLIP features, and a linear classifier generates pixel-wise predictions with standard cross-entropy loss; at inference, text prompts for all test-set categories (seen + novel/unseen) enable open-vocabulary segmentation.

### 10.4 Datasets and Evaluation Protocol

Six evaluation settings spanning weather condition, cloud type/opacity, and domain generalization, using: **OpenEarthMap-SAR** (1.5M segmented tiles, 35 regions in Japan/France/US, GSD 0.15–0.5m, 8 land-cover categories; synthetic OEM-thin/OEM-thick cloud variants via SatelliteCloudGenerator); **PIE-RGB-SAR** (Pearl River Delta, China; RGB from Google Satellite + SAR from GF-3 ultra-fine stripe mode, GSD ~0.5m/3m; PIE-clean and PIE-cloud tracks); **DDHR** (GF-2 RGB synthetically clouded via GIMP + GF-3 SAR resampled to 1m; DDHR-SK for Pohang/South Korea training, DDHR-CH for Xi'an/China cross-domain testing). Novel/unseen test classes (e.g., Road and Water for PIE/DDHR; Road, Water, Building for OpenEarthMap-SAR) test open-vocabulary generalization.

### 10.5 Main Results

Against six SOTA single-modality OVS baselines (CAT-Seg, EBSeg, FGAseg, GSNet, SegEarth-OV):

| Setting | CAT-Seg | EBSeg | GSNet | SegEarth-OV | FGAseg | **MM-OVSeg** |
|---|---|---|---|---|---|---|
| ① PIE-cloud→PIE-cloud | 54.5 | 50.8 | 57.0 | 45.1 | 51.6 | **57.7** |
| ② DDHR-SK→DDHR-SK | 54.2 | 51.1 | 55.0 | 17.6 | 51.6 | **73.1** |
| ③ OEM-thick→OEM-thick | 33.8 | 27.2 | 35.2 | 28.9 | 26.0 | **36.6** |
| ④ OEM-thin→OEM-thin | 29.5 | 25.6 | 37.0 | 18.5 | 32.8 | **40.2** |
| ⑤ PIE-clean→PIE-clean | 55.8 | 51.0 | 57.2 | 51.8 | 52.1 | **59.7** |
| ⑥ DDHR-SK→DDHR-CH (cross-domain) | 27.8 | 26.7 | 32.4 | 24.2 | 40.6 | **42.6** |
| **Mean** | 42.6 | 38.7 | 45.6 | 31.0 | 42.5 | **51.7** |

MM-OVSeg achieves the highest average performance (51.7% mIoU over six benchmarks) versus the second-best GSNet (45.6%), and unlike prior methods that excel on either seen *or* unseen classes only, it is consistently strong on both. It attains especially strong performance on the unseen "water" category (low, homogeneous SAR backscatter provides a reliable discrimination cue). Even on the clear-sky benchmark (⑤), where SAR contributions are less critical, MM-OVSeg still surpasses GSNet by 2.5% mIoU, and across cloud types it yields stable accuracy, indicating the model exploits complementary spectral/structural cues rather than overfitting to specific cloud patterns. Training on DDHR-SK and testing on DDHR-CH (cross-domain) degrades all training-required methods, but MM-OVSeg maintains a clear margin over competitors.

Ablations: on DDHR-SK, an optical-only baseline (no CMU or DEF) achieves 55.0% mIoU; adding DEF alone yields +9.1 points; combining CMU+DEF yields the full model's best 73.1% mIoU, showing the two modules are complementary. All three CMU loss functions (MSE, L1, InfoNCE) improve over the no-CMU baseline (64.1%), with **InfoNCE achieving the highest** (73.1%), beating MSE (67.7%) and L1 (69.0%). Feature visualization shows the CLIP visual encoder is less affected by cloud interference than DINO but has coarser attention (global semantics only); CLIP and DINO exhibit complementary attention patterns, and the fused representation gives finer spatial localization and better text-prompt alignment for both seen and unseen categories.

### 10.6 Implications for SatQuery AI Design

- MM-OVSeg is the most directly relevant existing work to the "Optical-SAR Analysis" evaluation criterion and "Cross-Modal Pair Analysis" mandatory scope — a complete, evaluated blueprint for a dedicated **Optical-SAR fusion specialist** (in spirit, since MM-OVSeg targets segmentation rather than VQA/captioning).
- Its central insight — that **only the dense/local encoder (DINO) needs SAR-specific adaptation, while the global semantic (CLIP text-aligned) encoder can remain RGB-only** — is a compute-efficient template: a lightweight SAR-alignment module (via contrastive loss on unlabeled co-registered pairs) can be trained while reusing an existing RGB-pretrained VLM backbone for global reasoning and language grounding.
- The **CMU (contrastive cross-modal alignment) + DEF (residual dual-encoder fusion)** two-stage recipe generalizes beyond segmentation: an analogous scheme could align a SAR encoder to an RGB-pretrained RS-VLM's visual space (e.g., feeding into GeoChat's or EarthDial's visual backbone) so natural-language grounding/captioning can draw on both modalities — directly satisfying *"Use the optical and SAR images together to identify built-up and water-covered regions."*
- The strong result on the unseen "water" class driven by SAR's homogeneous backscatter is a concrete, reusable justification for routing "water body" queries to a fusion-aware specialist rather than an optical-only model, especially under cloud cover.
- MM-OVSeg's evaluation protocol (intra-domain vs. cross-domain, varying cloud opacity) is a useful template for validating a SatQuery AI optical-SAR component, including deliberate testing under simulated cloud/haze contamination.
- Because MM-OVSeg outputs pixel-wise segmentation maps, not natural language, it would need pairing with a captioning/VQA layer (feeding mask + confidence into an LLM prompt) to produce an "evidence-grounded response" — reinforcing that the *agentic combination* of a segmentation/fusion specialist with a language-generation specialist is precisely the orchestration the problem statement calls for.

---

## 11. VRSBench: A Versatile Vision-Language Benchmark Dataset for Remote Sensing Image Understanding

**Authors:** Li, Ding, Elhoseiny (KAUST), NeurIPS 2024 Datasets & Benchmarks Track

### 11.1 Problem Addressed

Existing RS vision-language datasets suffer three compounding issues: most are single-task (captioning-only or VQA-only), forcing researchers to stitch heterogeneous datasets together; caption datasets (UCM-Captions, RSICD) are brief and lack object-level detail, while the one high-quality detailed-caption dataset (RSICap) is tiny (2,585 pairs), and large automatically-captioned datasets (RS5M, 5M pairs) lack human verification; visual grounding datasets (DIOR-RSVG) are built on scenes with mostly unique objects per category, making grounding artificially easy (38.36% of DIOR-RSVG objects are trivially distinguishable by category alone), and most VQA datasets use automatically generated, template-limited QA pairs, restricting linguistic diversity.

### 11.2 Dataset Construction — Semi-Automatic Pipeline

Four stages: **(1) Attribute Extraction** — from existing object-detection labels (DOTA-v2, DIOR), extract per-object category, bounding box (including **oriented bounding boxes, OBB** — a first for RS grounding datasets, since DOTA-v2 provides rotated boxes unlike DIOR-RSVG's horizontal-only boxes), color, position/size, and a flag for whether an object is unique within its category in the scene. **(2) Prompt Engineering** — an engineered instruction prompts GPT-4V to produce, per image, one detailed caption (3–7 sentences), 1–5 object-referring sentences, and 3–10 diverse QA pairs, returned as structured JSON. **(3) GPT-4V Inference** — the API is called with the image + extracted JSON attributes; hedging outputs ("not provided", "unknown") are filtered/regenerated (up to 5 retries), with surviving caveat fragments excised. **(4) Human Verification** — domain-expert-trained annotators correct every annotation (~120 sec/image, 1,004 total annotator-hours, $6,200 total cost), plus a second-pass re-verification of 2,000 images. Images are drawn from DOTA-v2 (18 categories, avg. 14.2 instances/patch) and DIOR (20 categories, avg. 3.3 instances/patch), merged into 26 unified categories.

### 11.3 Dataset Statistics

**29,614 images** (512×512), with 29,614 human-verified detailed captions (avg. 52 words / ~4 sentences; 9,588-word vocabulary; 1,526,338 total words), 52,472 object-referring sentences (skewed toward "vehicle" ~39%; ~47% "small" objects), and 123,221 QA pairs (3–10 per image) across 10 question types (object existence 20%, position 19%, quantity 18%, scene type 13%, category 12%, color 8%, plus smaller shares for size, direction, shape, complex reasoning). VRSBench is the only prior dataset with non-trivial values in **all** of Captions/Grounding/VQA/Human-verification simultaneously. Official train/test split follows DOTA/DIOR's own splits (20,264 train / 9,350 test images), avoiding a custom re-split that might leak.

### 11.4 Three Benchmark Tasks and Evaluation

**VRSBench-Cap** (detailed captioning): BLEU-1..4, METEOR, ROUGE-L, CIDEr, plus **CLAIR** (GPT-4-judged caption quality), since n-gram metrics poorly suit long, detailed captions. **VRSBench-Ref** (visual grounding): Accuracy@IoU (0.5, 0.7) on horizontal boxes (OBB in supplementary), separately reported for **unique vs. non-unique** objects — the paper's key methodological innovation, since non-unique-object grounding is measurably harder for every model tested. **VRSBench-VQA**: accuracy per question type, judged by **GPT-4 as a semantic-equivalence checker** (accepting synonyms, e.g., "pond" ≈ "swimming pool") rather than brittle exact-string-match.

### 11.5 Benchmarked Models & Results

LLaVA-1.5, MiniGPT-v2, GeoChat, and Mini-Gemini (all CLIP-ViT-L/14 + Vicuna-7B, LoRA rank 64, 5 epochs) were fine-tuned jointly on all three tasks; GPT-4V was evaluated zero-shot (without object-attribute context) as an upper-bound reference. **Captioning**: fine-tuned LLaVA-1.5 achieves the best conventional metrics (BLEU-1 48.1, CIDEr 33.9), while GPT-4V achieves the best CLAIR score (0.83) — unsurprising since CLAIR itself uses GPT-4 as judge. The **un-fine-tuned GeoChat baseline collapses** (BLEU-1 13.9, CIDEr 0.4) versus its fine-tuned counterpart (BLEU-1 46.7, CIDEr 28.2) — the single clearest demonstration in this entire corpus that domain fine-tuning is not optional. **Grounding**: fine-tuned **GeoChat is the best grounder** (Acc@0.5 = 49.8% overall; 57.4%/44.5% unique/non-unique), yet even this best result is modest — GPT-4V without object-attribute prompting performs worst (5.1% Acc@0.5), confirming explicit object/attribute context is essential for RS grounding. **VQA**: fine-tuned models reach 76–78% overall accuracy (Mini-Gemini best at 77.8%) versus only 40.8% for un-fine-tuned GeoChat and 65.6% for zero-shot GPT-4V — again a >35-point jump from fine-tuning.

### 11.6 Implications for SatQuery AI Design

- **VRSBench is explicitly named as one of the three public evaluation benchmarks**; its exact task definitions and metrics (BLEU/METEOR/ROUGE/CIDEr/CLAIR for captioning; Acc@IoU split by unique/non-unique for grounding; GPT-4-judged semantic accuracy for VQA) should be adopted verbatim as an internal evaluation protocol, ensuring apples-to-apples comparability with published baselines.
- GeoChat is confirmed as a strong, purpose-built RS multi-task baseline (best grounder, competitive VQA/captioning) and publicly available — a highly attractive candidate starting checkpoint for the core specialist backbone(s).
- The **unique-vs-non-unique grounding split** is a crucial design point: SatQuery AI's grounding specialist should be stress-tested specifically on scenes with multiple same-category objects (e.g., "highlight the water body" when several exist), matching the representative query's implicit ambiguity that must be resolved via spatial/contextual reasoning.
- The collapse of un-adapted VLMs (GeoChat w/o fine-tuning: BLEU-1 13.9, VQA 40.8% vs. 46.7/76.0% after fine-tuning) is the strongest single evidence for the problem statement's hard constraint against generic unadapted LLM/VLM submissions — worth citing directly in a technical write-up.
- VRSBench's semi-automatic GPT-4V + human-verification pipeline ($6,200 for ~30K images) is a reusable, cost-quantified recipe to generate additional bespoke instruction-tuning data (e.g., synthetic optical-SAR fusion QA pairs) if the three named public datasets prove insufficient.
- The **OBB grounding support** is a forward-looking capability beyond DIOR-RSVG's horizontal-only boxes; exposing OBB as an option for "visual evidence" output would better suit the often-rotated geometry of real satellite objects (ships, runways, buildings at oblique angles).
- Confirms **CLIP-ViT-L/14 + Vicuna-7B + LoRA rank-64** as a near-field-standard recipe across three independently developed systems (RS-LLaVA, GeoChat, VRSBench's own baselines) — a strong convergent signal for the core VLM technology stack.

---

# Part E: Cross-Paper Synthesis and Design Recommendations

## 12. Cross-Cutting Themes Across All Ten Papers

1. **Domain adaptation beats scale.** Across BigEarthNet.txt (RS-InternVL, 1B params), GeoChat (7B, LoRA-tuned), EarthDial (4B), RS-LLaVA (7B/13B), and the Qwen change-VQA study (0.8B–9B), small domain-adapted models consistently outperform much larger general-purpose VLMs (GPT-4o, GPT-5.2, Qwen3-VL zero-shot) on RS-specific tasks — directly validating the problem statement's premise that a general-purpose LLM/VLM cannot reliably perform these specialized tasks without adaptation.

2. **Naive multimodal input ≠ multimodal understanding.** BigEarthNet.txt shows that simply feeding extra spectral/SAR channels into an RGB-pretrained model can *hurt* performance without dedicated fine-tuning; reBEN's ablation shows SAR contributes only a modest lift once S2 is present unless properly fused; MM-OVSeg shows a *targeted* contrastive-alignment step (CMU) is what actually unlocks SAR's benefit. This has direct implications for how SatQuery AI must build its cross-modal specialist — genuine alignment training, not channel concatenation.

3. **No single existing model covers the full SatQuery AI mandate.** GeoChat covers single-image tasks (VQA/captioning/grounding) but not temporal or SAR data. RS-LLaVA covers joint captioning+VQA but not grounding, change, or fusion. CDVQA and the Qwen re-benchmark cover bi-temporal change-VQA but only for optical RGB. EarthDial covers multi-sensor + multi-temporal conversational tasks but does not report explicit joint-fusion textual reasoning the way MM-OVSeg's dense features imply. MM-OVSeg covers optical-SAR fusion but only for segmentation, not natural language. This fragmentation is the direct empirical justification for SatQuery AI's **agentic, multi-specialist architecture** rather than a single end-to-end model.

4. **Efficient adaptation recipes converge on LoRA + frozen-backbone strategies.** RS-InternVL (frozen ViT + LoRA on the LLM), GeoChat (frozen CLIP + LoRA on Vicuna, rank 64), RS-LLaVA (frozen CLIP-ViT + LoRA on Vicuna, rank 64), and the Qwen change-VQA study (frozen ViT/PatchMerger + LoRA rank 16 on attention projections) all converge on the same practical recipe: freeze large pretrained visual backbones, add small modality-specific projection/fusion modules, and fine-tune the LLM's attention weights via LoRA. This recipe recurs across five independently developed systems from different research groups and years, making it the strongest, most empirically validated starting point for SatQuery AI's own remote-sensing fine-tuning component. The broader survey (Paper 9) explicitly recommends LoRA as future direction, citing 10,000× fewer trainable parameters and 3× lower GPU memory versus full fine-tuning.

5. **Change-detection and cross-modal reasoning both benefit from explicit difference/fusion modules, not naive concatenation.** CDVQA's Change Enhancing Module and MM-OVSeg's Dual-Encoder Fusion both demonstrate that simple concatenation or subtraction underperforms a dedicated attention/alignment mechanism designed to highlight what is different (temporally) or complementary (across sensors).

6. **Counting, quantity estimation, and fine-grained magnitude/ratio discrimination are the recurring weak point.** RS-LLaVA struggles with counting; the Qwen change-VQA study's hardest categories are smallest-change discrimination and change-ratio bucketing (30–60% accuracy vs. 80–85% for binary/directional questions); VRSBench's own QA taxonomy allocates 18% of questions to "quantity," a known difficulty area. SatQuery AI's confidence-estimation module should treat these query types as systematically lower-confidence.

7. **Fine-tuning is not optional — it is a >30-point accuracy swing.** RS-InternVL improves binary VQA from 61.96% (best generalist) to 73.29%; VRSBench shows GeoChat collapsing from 46.7% (fine-tuned) to 13.9% BLEU-1 (un-fine-tuned) on captioning and from 76.0% to 40.8% on VQA. These ablations, present across independently authored papers, are the strongest possible justification for the problem statement's blanket rule that a generic unadapted LLM/VLM will not satisfy the requirements.

## 13. Dataset-to-Requirement Mapping

| SIH26167 Mandatory Requirement | Best-supported dataset(s) | Best-supported baseline architecture |
|---|---|---|
| Remote-sensing adaptation (fine-tuning) | BigEarthNet.txt / reBEN (S1+S2) | Frozen ViT/CLIP encoder + LoRA-adapted LLM (RS-InternVL recipe) |
| Single-image VQA | BigEarthNet.txt VQA/MCQ, RSVQA (LR/HR), RSIVQA, VRSBench-VQA | RS-LLaVA (Vicuna-13B, LoRA), GeoChat, RS-InternVL |
| Captioning (additional single-image task) | BigEarthNet.txt captions, VRSBench-Cap, UCM/Sydney/RSICD | LLaVA-1.5 / GeoChat fine-tuned on VRSBench; RS-InternVL |
| Region grounding (alternate additional task) | BigEarthNet.txt referring-expression, VRSBench-Ref (harder, non-unique-aware), DIOR-RSVG | GeoChat (best grounder in VRSBench study) |
| Multitemporal change VQA | CDVQA | Qwen3.5-2B + LoRA (best accuracy/efficiency); CDVQA baseline + CEM |
| Optical-SAR cross-modal analysis | BigEarthNet.txt / reBEN S1+S2 fusion; MM-OVSeg's CMU-Data | ResNet-50/101 fusion backbone (classification proxy); MM-OVSeg CMU+DEF (segmentation proxy); no dedicated generative fusion-VQA baseline found — **a genuine gap** SatQuery AI's own agentic system must fill |

## 14. Identified Gaps SatQuery AI Must Address Independently

None of the ten papers provide a ready-made **generative, natural-language optical-SAR fusion QA/description model**. reBEN and BigEarthNet.txt only demonstrate fusion for closed-set multi-label *classification* or same-time captioning, not open-ended cross-modal reasoning; MM-OVSeg fuses optical and SAR but outputs pixel-wise *segmentation*, not language. This is the one mandatory SatQuery AI capability with the least direct precedent in the surveyed literature, meaning it likely requires either **(a)** a custom lightweight fusion head feeding a shared VLM decoder, trained on BigEarthNet-derived pseudo-captions, or **(b)** a two-step pipeline where a fusion classifier/segmenter (à la reBEN's S1+S2 ResNet or MM-OVSeg's CMU+DEF) produces structured land-cover/change signals that are then verbalized by the same LLM decoder used for VQA — an approach consistent with the problem statement's own emphasis on "combining outputs" rather than requiring one model to natively fuse SAR and optical pixels end-to-end.

## 15. Confidence & Evaluation Design Signals

Across the BigEarthNet.txt, RS-LLaVA, and change-VQA papers, the recurring weak points for RS-VLMs are **counting/quantity estimation** and **fine-grained magnitude or smallest-change discrimination**. SatQuery AI's agentic controller should treat these query types as systematically lower-confidence regardless of which specialist tool answers them, and its "confidence information" output (mandatory per the problem statement) should be calibrated with this prior in mind rather than uniform across question types.

## 16. Benchmark-Alignment Checklist for SatQuery AI Evaluation

- Report VQA using the **VRSBench GPT-4-judged semantic accuracy** protocol and/or standard RSVQA per-question-type accuracy (both precedented) and BigEarthNet.txt's binary/MCQ accuracy split.
- Report captioning using **BLEU-1..4/METEOR/ROUGE-L/CIDEr** at minimum, and consider CLAIR if an LLM-judge is available.
- Report grounding, if implemented, split by **unique vs. non-unique** referents at IoU thresholds 0.5 and 0.7 (VRSBench convention), and consider oriented bounding boxes given ISRO's Cartosat/RISAT geometry.
- Report Change-VQA using the **CDVQA per-question-type + AA/OA** protocol, benchmarking against published VisTA/SOBA/CDVQA-baseline and Qwen3.5 numbers.
- Report Optical-SAR fusion using an MM-OVSeg-style protocol adapted for generative tasks — matched clear-sky vs. cloud-contaminated conditions, and intra-domain vs. cross-domain generalization.
- For remote-sensing adaptation evidence, document the **exact frozen/trainable parameter split** and LoRA configuration (rank, target modules) as nearly every method paper surveyed does, since judges evaluating "Remote-Sensing Adaptation" will look for this level of specificity.

## 17. Convergent Architectural Recipe (Summary)

Every RS-VLM fine-tuning paper surveyed — RS-InternVL, GeoChat, RS-LLaVA, and the Qwen change-VQA study — independently converges on the same low-cost adaptation recipe: **freeze a large pretrained vision encoder (CLIP-ViT or a Qwen/InternVL-style ViT) and a large pretrained LLM decoder, and apply LoRA only to the decoder's attention projection matrices** (with the projection/alignment MLP either pretrained separately or also frozen). MM-OVSeg's optical-SAR analogue — freeze both RGB and CMU-aligned SAR DINO encoders, keep only CLIP and the fusion/decoder trainable — extends the same freeze-most/adapt-little philosophy to the cross-modal setting. This should be SatQuery AI's default fine-tuning strategy for whichever specialist model(s) satisfy the "Remote-Sensing Adaptation" mandatory requirement: it is compute-cheap, well-validated across at least five independently developed systems, and directly measurable via the fine-tuned-vs-unfine-tuned ablations reported throughout this survey (consistently 30+ point accuracy swings from fine-tuning alone).

---

*End of consolidated literature survey. This document merges and supersedes the two earlier draft parts (Part 1: BigEarthNet.txt, CDVQA, EarthDial, GeoChat, MM-OVSeg; Part 2: reBEN, Qwen Change-VQA, RS-LLaVA, VLM survey, VRSBench).*
