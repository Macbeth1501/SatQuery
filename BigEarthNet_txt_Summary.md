# BigEarthNet.txt — Paper Summary

## 1. Paper Overview

**Title:** BigEarthNet.txt: A Large-Scale Multi-Sensor Image-Text Dataset and Benchmark for Earth Observation  
**Authors:** Johann-Ludwig Herzog, Mathis Jürgen Adler, Leonard Hackel, Yan Shu, Angelos Zavras, Ioannis Papoutsis, Paolo Rota, Begüm Demir  
**Version:** arXiv:2603.29630v2, April 2026  
**Website:** https://txt.bigearth.net

### Core Idea

BigEarthNet.txt is a large-scale **multi-sensor remote-sensing image-text dataset** designed to improve Vision-Language Models (VLMs) for Earth Observation (EO).

It combines co-registered:

- **Sentinel-1 (S1)** Synthetic Aperture Radar (SAR)
- **Sentinel-2 (S2)** multispectral imagery
- Rich natural-language annotations covering spatial, semantic, geographic, and environmental information.

The central motivation is that most existing VLMs and remote-sensing image-text datasets are heavily focused on **RGB imagery**, while Earth Observation often requires information beyond the visible spectrum.

---

# 2. Problem Statement

Modern satellite systems generate enormous quantities of Earth Observation data. Natural language could provide an intuitive way to search and interpret this data, but current VLMs have important limitations.

### Main problems identified

1. **RGB-centric VLMs**
   - Most general-purpose VLMs are pretrained on RGB image-text data.
   - Remote-sensing images contain additional spectral information that RGB models cannot fully exploit.

2. **Insufficient multi-sensor datasets**
   - Existing datasets rarely provide large-scale, co-registered multi-sensor data.
   - Combining sensors such as SAR and multispectral imagery can provide complementary information about land-use/land-cover (LULC).

3. **Limited textual diversity**
   - Many earlier datasets contain short captions or limited annotation types.
   - They often do not capture spatial relationships, counts, areas, geographic context, or detailed LULC structure.

4. **Weak evaluation of complex reasoning**
   - Existing benchmarks do not adequately test whether VLMs can reason about complex spatial and spectral content.

The paper therefore targets the lack of **large-scale, multi-sensor, semantically rich image-text data** for remote sensing.

---

# 3. BigEarthNet.txt Dataset

BigEarthNet.txt contains:

| Property | Value |
|---|---:|
| Co-registered S1-S2 image pairs | **464,044** |
| Text annotations | **~9.6 million** |
| Text corpus | **~50 million words** |
| Sentences | **~2.1 million** |
| Average words/caption | **107** |
| Average sentences/caption | **4.5** |
| Unique vocabulary terms | **12,394** |
| Downstream tasks | **15** |
| Broad task categories | **4** |
| Benchmark image pairs | **1,082** |
| Benchmark annotations | **15,029** |

The images originate from **BigEarthNet v2.0**, which contains 549,488 S1-S2 image pairs covering ten European countries. The authors filter out images affected by issues such as seasonal snow, clouds, cloud shadows, and unclassified reference-map pixels, resulting in 464,044 pairs.

---

# 4. Sensors Used

## Sentinel-1

Sentinel-1 provides **Synthetic Aperture Radar (SAR)** information.

SAR can capture physical characteristics that complement optical imagery and is useful for understanding land surfaces under conditions where optical imagery may be limited.

## Sentinel-2

Sentinel-2 provides **multispectral imagery**.

The paper notes that Sentinel-2 contains 13 spectral bands with different spatial resolutions. Spectral information beyond RGB can help distinguish visually similar but semantically different LULC classes.

### Why combine S1 + S2?

Different sensors measure different physical properties. Their combination can provide complementary information and potentially improve understanding of complex land-use/land-cover scenes.

---

# 5. Annotation Types

BigEarthNet.txt supports four major categories:

1. **Image Captioning**
2. **Binary Visual Question Answering (VQA)**
3. **Multiple-Choice VQA (MCQ)**
4. **Referring Expression Detection**

Together, these cover **15 tasks**.

### Tasks include

- Presence
- Area
- Counting
- Adjacency
- Relative Position
- Country
- Season
- Climate Zone
- Referring LULC Detection
- Referring Point Detection
- Captioning

The dataset is designed to test not only image recognition but also **spatial reasoning, geographic reasoning, language understanding, and localization**.

---

# 6. Caption Generation Pipeline

The annotation pipeline has three main stages:

## Stage 1 — Template-Based Caption Generation

Information is extracted directly from the LULC reference maps.

The system extracts:

- Presence of LULC classes
- Number of contiguous regions/instances
- Total area of each class
- Area of individual instances
- Pairwise spatial adjacency

Area values are rounded to the nearest **1,000 m²** to reduce label noise.

LULC classes are divided into three coverage tiers:

- **Primary:** >25% of image
- **Secondary:** 5–25%
- **Marginal:** <5%

Additional contextual information is added:

- Acquisition season
- Country/location
- Köppen-Geiger climate zone

This produces factually grounded template captions.

---

# 7. LLM-Based Linguistic Augmentation

Template captions are factually reliable but linguistically repetitive.

To increase linguistic diversity, the authors use **quantized Llama-4-Scout-17B**.

The process contains:

### 1. Paraphrasing

The model changes lexical and syntactic structure while being instructed not to introduce unsupported information.

### 2. Self-Refinement

The paraphrased caption is compared against the original template.

The model attempts to:

- Remove hallucinated information
- Restore missing information
- Maintain factual consistency

A manual evaluation of **3,209 randomly sampled augmented captions** produced:

- **93.76% average correctness**
- **77.50%** satisfied all four quality criteria simultaneously

The four criteria were:

- Linguistic correctness
- Factual accuracy
- Completeness
- Absence of generation artifacts

---

# 8. VQA Generation

The dataset also generates question-answer pairs.

## Binary VQA

Questions focus on:

- Presence
- Count
- Size/area
- Adjacency

The authors deliberately construct negative examples so that the answer cannot always be determined simply by checking whether a class is absent.

## Multiple-Choice VQA

MCQs additionally test:

- Relative position
- Country
- Season
- Climate zone

Each question has:

- 1 correct answer
- 3 incorrect answers

Incorrect options are sampled using analogous principles to the binary VQA generation.

---

# 9. Referring Expression Detection

The dataset includes natural-language instructions requiring a model to locate LULC instances.

Two forms are used:

### Referring LULC Detection

The model receives a textual description and must predict the bounding box of the referenced LULC instance.

### Referring Point Detection

The model is given a point inside the target instance and must predict its enclosing bounding box.

Approximately **80% of image pairs contain at least one referring-expression detection annotation**.

---

# 10. Text Statistics

The caption corpus contains approximately:

- **50 million words**
- **2.1 million sentences**
- **12,394 unique terms**

Average caption:

- **107 words**
- **4.5 sentences**

The dataset achieves an **MTLD lexical diversity score of 64.69**.

According to the paper, this makes BigEarthNet.txt approximately **1.7× more lexically diverse** than the largest existing remote-sensing dataset containing images with more than three bands.

The captions are also semantically richer, with more words per sample than comparable datasets.

---

# 11. Benchmark Split

Because LLM-generated captions can contain hallucinated information, the authors create a manually verified benchmark.

### Benchmark

- **1,082 image pairs**
- **15,029 text annotations**

Composition:

| Annotation | Count |
|---|---:|
| Binary VQA | 6,927 |
| Multiple-choice VQA | 5,550 |
| Captions | 970 |
| Referring expression detection | 1,582 |

The benchmark balances binary and MCQ answer choices to reduce answer bias.

Annotations are also balanced across LULC classes as far as the natural class distribution permits.

---

# 12. Dataset Train/Validation/Test Split

The complete dataset is divided according to the BigEarthNet v2.0 split:

| Split | Image pairs | Text annotations |
|---|---:|---:|
| Train | 229,114 | 4,674,281 |
| Validation | 118,095 | 2,454,690 |
| Test | 116,835 | 2,424,991 |

The manually verified benchmark is constructed from the test split.

---

# 13. Comparison With Existing Datasets

The paper compares BigEarthNet.txt against datasets including:

- UCM-Captions
- Sydney-Captions
- RSICD
- RSITMD
- NWPU-Captions
- GAIA
- Git-10M
- RSVQAxBEN
- RS5M
- RSTeller
- Landsat30-AU
- ChatEarthNet
- MS-CLIP

The key advantage claimed by BigEarthNet.txt is the combination of:

**large scale + co-registered multi-sensor imagery + diverse annotations + multiple downstream tasks + manual benchmark verification.**

---

# 14. Evaluation of Existing VLMs

The authors evaluate both general-purpose computer-vision VLMs and remote-sensing VLMs.

### CV VLMs

- GPT
- Qwen
- GLM
- LLaVA
- InternVL

### RS VLMs

- GeoChat
- LHRS-Bot
- SkyEyeGPT
- EarthDial
- EarthMind

Most models receive only RGB information.

EarthDial and EarthMind are also tested with multispectral/multi-sensor configurations.

---

# 15. Key Findings From Existing VLM Evaluation

The experiments show that current VLMs generally struggle with the complex tasks in BigEarthNet.txt.

Important observations:

- General-purpose CV VLMs often outperform specialized RS VLMs.
- This is attributed partly to stronger generalization and instruction-following abilities.
- Many RS VLMs are mainly trained on tasks that can be solved from RGB information.
- Models accepting multispectral or multi-sensor input do **not automatically gain an advantage** because their training data has largely been RGB-based.
- Performance is better on tasks resembling common pretraining objectives, such as simple class presence.
- Complex spatial reasoning, LULC interpretation, and localization remain difficult.

This suggests that the problem is substantially related to **training-data limitations**, rather than only model architecture.

---

# 16. RS-InternVL

To test whether better training data can solve the problem, the authors adapt **InternVL-3-1B** into a multi-sensor model called **RS-InternVL**.

### Architecture

The model introduces modality-specific branches for:

- Sentinel-1
- Sentinel-2

Pretrained Vision Transformers (ViTs) produce image patch embeddings.

These embeddings are projected into the LLM embedding space and combined with:

- RGB tokens
- S1 tokens
- S2 tokens
- Text instruction tokens

The resulting sequence is passed to the language model.

---

# 17. Efficient Fine-Tuning

To preserve pretrained representations and reduce computation:

- ViT backbones are frozen.
- Only modality-specific projection layers and LoRA adapters are trained.
- LoRA configuration:
  - Rank = 8
  - α = 32
  - Dropout = 0.1

Only **5.8 million parameters** are trained out of approximately **1.1 billion total parameters**.

The S1/S2 encoders are initialized using BigEarthNet-pretrained ViTs.

Only the **10 m and 20 m S2 bands** are processed because the 60 m bands are primarily used for cloud screening and atmospheric correction and are considered less informative for semantic understanding.

---

# 18. Training Setup

The paper reports:

- Linear warm-up + cosine annealing
- Learning rate starts at **10⁻⁶**
- Learning rate increases to **10⁻⁴**
- Warm-up lasts for the first **1% of steps**
- Cosine decay follows
- Training for **1 epoch**
- Training uses combined train + validation sets
- Evaluation uses the manually verified benchmark

Fine-tuning required approximately **2 days on four NVIDIA H200 GPUs**.

---

# 19. Main Results

The most important comparison is:

| Model | Captioning BLEU-4 | Binary VQA | MCQ | Ref. Exp. Detection mIoU |
|---|---:|---:|---:|---:|
| SOTA RS | 1.66 | 58.38 | 35.26 | 16.18 |
| SOTA CV | 0.96 | 61.96 | 37.55 | 31.73 |
| **RS-InternVL** | **34.04** | **73.29** | **51.49** | **65.84** |

RS-InternVL substantially outperforms the existing baselines across all four major task categories.

---

# 20. Central Research Finding

The paper argues that current VLM limitations on complex remote-sensing tasks are largely caused by **insufficient appropriate training data**.

The evidence is:

1. Existing VLMs perform poorly on complex multi-sensor tasks.
2. Simply allowing some models to consume multispectral/multi-sensor input does not guarantee improvement.
3. A relatively small 1B-parameter model can achieve major gains after being adapted for multi-sensor input and fine-tuned on BigEarthNet.txt.
4. Only 5.8M parameters are trained in the proposed adaptation.

The paper therefore emphasizes the importance of **large-scale, diverse, multi-sensor image-text datasets**.

---

# 21. Key Contributions

### Contribution 1 — Large-scale dataset

Introduces **464,044 co-registered Sentinel-1/Sentinel-2 image pairs** with approximately **9.6M text annotations**.

### Contribution 2 — Diverse annotations

Unifies:

- Captioning
- Binary VQA
- MCQ VQA
- Referring expression detection

### Contribution 3 — Multi-sensor learning

Provides data that combines SAR and multispectral imagery.

### Contribution 4 — Manually verified benchmark

Creates a smaller, curated benchmark for reliable VLM evaluation.

### Contribution 5 — Multi-sensor VLM adaptation

Adapts InternVL-3-1B to accept multi-sensor remote-sensing inputs.

### Contribution 6 — Evidence for data-centric improvement

Shows that suitable training data can dramatically improve performance even without training a huge model from scratch.

---

# 22. Overall Takeaway

**BigEarthNet.txt is essentially a data-centric solution to the problem of applying Vision-Language Models to complex Earth Observation data.**

The paper identifies a gap:

> Existing VLMs are mostly trained on RGB image-text data, while remote sensing requires richer spectral, spatial, and multi-sensor understanding.

It addresses this by creating a large dataset containing:

**Sentinel-1 + Sentinel-2 + LULC maps + rich language annotations + spatial reasoning tasks.**

The experiments demonstrate that current VLMs struggle with this data, but targeted multi-sensor adaptation and fine-tuning can produce major improvements.

The most significant result is the jump of RS-InternVL to:

- **34.04 BLEU-4** for captioning
- **73.29%** binary VQA accuracy
- **51.49%** MCQ accuracy
- **65.84% mIoU** for referring expression detection

The paper concludes that adequate, diverse training data is critical for enabling VLMs to interact naturally with complex Earth Observation imagery.

---

# 23. Useful Research Insights

For someone studying this paper, the most important concepts to remember are:

### Dataset Problem
**Lack of large-scale, multi-sensor, richly annotated RS image-text datasets.**

### Data
**464,044 S1-S2 image pairs + ~9.6M annotations.**

### Modalities
**Sentinel-1 SAR + Sentinel-2 multispectral.**

### Language
**Captions + binary VQA + MCQ + referring expressions.**

### Reasoning
**Presence, area, counting, adjacency, relative position, location, season, climate, and spatial localization.**

### Annotation Strategy
**Reference-map attributes → templates → LLM paraphrasing → self-refinement → VQA/referring-expression generation.**

### Quality Control
**Manual evaluation of augmented captions + manually verified benchmark split.**

### Model
**RS-InternVL based on InternVL-3-1B with modality-specific branches and LoRA.**

### Main Finding
**Better multi-sensor training data can substantially improve VLM performance.**

---

# 24. One-Paragraph Summary

BigEarthNet.txt is a large-scale multi-sensor image-text dataset for Earth Observation created to address the limitations of RGB-centric Vision-Language Models in remote sensing. It contains 464,044 co-registered Sentinel-1 SAR and Sentinel-2 multispectral image pairs with approximately 9.6 million text annotations covering captioning, binary VQA, multiple-choice VQA, and referring expression detection across 15 tasks. Captions are generated from LULC reference maps and enriched using LLM-based paraphrasing and self-refinement, while a manually verified benchmark of 1,082 image pairs enables reliable evaluation. Experiments show that existing VLMs struggle with complex spectral and spatial reasoning, but adapting InternVL-3-1B for multi-sensor input and fine-tuning it on BigEarthNet.txt produces large improvements across all evaluated tasks. The paper therefore provides strong evidence that suitable large-scale multi-sensor image-text data is a key requirement for effective VLM-based Earth Observation.

---

## Source

This summary is based on the uploaded paper:

**Herzog et al., “BigEarthNet.txt: A Large-Scale Multi-Sensor Image-Text Dataset and Benchmark for Earth Observation.”**

Source content: uploaded PDF.
