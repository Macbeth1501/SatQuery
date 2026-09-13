# SatQuery AI (SIH 167)
### An Interactive Vision-Language Assistant for Multimodal Remote Sensing Image Analysis through Text Queries

---

## Table of Contents

1. [Core Idea & Executive Summary](#1-core-idea--executive-summary)
2. [Problem Statement Context](#2-problem-statement-context)
3. [RSVP Proposed Solution Architecture](#3-rsvp-proposed-solution-architecture)
4. [Component Breakdown](#4-component-breakdown)
5. [System Scope](#5-system-scope)
6. [Data Pipeline & Preprocessing](#6-data-pipeline--preprocessing)
7. [Research Depth & Literature Foundation](#7-research-depth--literature-foundation)
8. [Model Training & Evaluation Strategy](#8-model-training--evaluation-strategy)
9. [Scalability Measures](#9-scalability-measures)
10. [Deployment & Infrastructure](#10-deployment--infrastructure)
11. [Security, Privacy & Compliance](#11-security-privacy--compliance)
12. [Architecture Decision Records (ADRs)](#12-architecture-decision-records-adrs)
13. [Risks & Mitigation Strategy](#13-risks--mitigation-strategy)
14. [Success Metrics & KPIs](#14-success-metrics--kpis)
15. [Implementation Roadmap](#15-implementation-roadmap)
16. [Team & Skill Requirements](#16-team--skill-requirements)
17. [Future Enhancements](#17-future-enhancements)
18. [Glossary](#18-glossary)

---

## 1. Core Idea & Executive Summary

**SatQuery AI** is an intelligent, conversational assistant that processes multi-sensor satellite imagery (**Optical** and **SAR — Synthetic Aperture Radar**) and responds to complex natural language queries in real time. Instead of relying on manual GIS scripting, tedious raster algebra, or specialized remote-sensing software, users can simply **chat with Earth Observation (EO) data** to perform tasks such as:

- **Multi-temporal Change Detection** — *"Show me deforestation between 2024 and 2026."*
- **Visual Question Answering (RS-VQA)** — *"How many aircraft are on the tarmac?"*
- **Visual Grounding** — *"Locate all industrial storage tanks."*
- **Cross-Modal Reasoning** — *"Is there construction activity visible under cloud cover?"*
- **Disaster & Anomaly Assessment** — *"Highlight flooded regions compared to last month's baseline."*

The platform democratizes access to satellite intelligence — enabling policymakers, defense analysts, urban planners, disaster-response teams, and environmental researchers to extract actionable geospatial insights **without needing GIS expertise**.

### Why This Matters
- India's growing constellation of EO satellites (Cartosat, RISAT, EOS series) generates petabytes of imagery that remain **underutilized** due to the steep technical barrier of interpretation.
- Analysts spend disproportionate time on **manual annotation and interpretation** rather than decision-making.
- A natural-language interface collapses this barrier, turning raw pixels into **structured, decision-ready intelligence** in seconds.

---

## 2. Problem Statement Context

| Attribute | Detail |
|---|---|
| **SIH Problem ID** | SIH 167 |
| **Domain** | Remote Sensing / Geospatial AI / Vision-Language Models |
| **Target Users** | Defense & surveillance analysts, disaster management authorities, urban planning bodies, agriculture & forestry departments, environmental monitoring agencies |
| **Core Challenge** | Bridging unstructured natural language with structured, multi-sensor geospatial raster data to enable real-time, explainable EO analysis |
| **Expected Outcome** | A deployable prototype capable of ingesting optical/SAR imagery and answering free-form text queries with grounded visual and geospatial outputs |

---

## 3. RSVP Proposed Solution Architecture

The system uses the **RSVP (Remote-Sensing Semantic Vision & Processing)** framework — a layered architecture designed to bridge unstructured text queries with raw geospatial raster pixel matrices.

```
                    +--------------------------------------------------+
                    |         User Interface (Web / API / GIS Plugin)  |
                    +------------------------+-------------------------+
                                             |
                                  [Natural Language Query]
                                             v
                    +--------------------------------------------------+
                    |     Orchestration Engine (Agentic Routing Layer)  |
                    +----+-------------------+--------------------+----+
                         |                   |                    |
         [Visual Grounding / QA]     [Change Detection]    [Optical-SAR Fusion]
                         v                   v                    v
    +------------------------------+ +-------------------+ +-----------------------+
    |  RS-Vision Language Core     | | Multi-Temporal    | | Cross-Modal Mapping   |
    |  (ViT-H + GeoChat-LLaVA)     | | Alignment Net     | | Layer (SAR-to-Optical)|
    +--------------+---------------+ +---------+---------+ +-----------+-----------+
                   |                           |                        |
                   +---------------------------+------------------------+
                                             |
                                             v
                          +------------------------------------+
                          | Post-Processing & Raster Alignment |
                          +-----------------+------------------+
                                            |
                          +-----------------v------------------+
                          |  Structured Response Generator     |
                          | (COCO JSON / GeoJSON / Text / Mask) |
                          +------------------------------------+
```

### Data Flow Narrative
1. A user submits a **natural language query** through a web dashboard, REST API, or a GIS plugin (e.g., QGIS extension).
2. The **Orchestration Engine** — an agentic router built on top of an intent-classification layer — decomposes the query into sub-tasks (grounding, VQA, change detection, or fusion) and dispatches them to the relevant expert module.
3. Each expert module operates on the raw or pre-tiled raster data, producing intermediate embeddings, masks, or textual reasoning traces.
4. Outputs converge at the **Post-Processing & Raster Alignment** stage, where georeferencing, coordinate reprojection (e.g., WGS84 ↔ UTM), and mask stitching occur.
5. The **Structured Response Generator** packages results into the format most useful to the consumer — human-readable text, a GeoJSON polygon, a segmentation mask overlay, or a COCO-style annotation file for downstream ML pipelines.

---

## 4. Component Breakdown

### Module A — Multimodal Encoder Alignment
- Combines multi-sensor input streams using a hierarchical **Vision Transformer (ViT-H/14)**.
- Introduces a **projection/adapter layer** to bridge the physical and statistical gap between optical bands (surface reflectance, RGB/NIR) and SAR data (radar backscatter intensity, phase/coherence).
- Handles resolution mismatches between sensors via learned upsampling and patch re-alignment.

### Module B — Conversational Geospatial Engine
- Utilizes an open-source multimodal backbone (e.g., **LLaVA-1.6-Mistral-7B**) fine-tuned via **Parameter-Efficient Fine-Tuning (PEFT/LoRA)**.
- Trained/fine-tuned on domain datasets such as **RSVQA**, **EarthGPT**, **GeoChat-Instruct**, and **ChangeVQA**.
- Maintains multi-turn conversational context, allowing follow-up queries like *"Now compare that to the previous year."*

### Module C — Spatial Grounding Head
- Integrates a promptable segmenter (**SAM-RS**, a remote-sensing-adapted variant of Segment Anything Model) that converts attention/activation maps into precise **GeoJSON coordinates** and boundary geometry masks.
- Supports point, box, and text-prompted segmentation for flexible grounding.

### Module D — Multi-Temporal Alignment Network *(expanded)*
- Performs **co-registration** of two or more epochs of imagery (T₁, T₂, …, Tₙ) to a common spatial reference frame.
- Applies **Siamese-network-based change encoders** to detect and quantify pixel-level and object-level differences.
- Outputs a change-intensity heatmap plus a natural-language summary of significant changes.

### Module E — Cross-Modal Mapping Layer (SAR-to-Optical) *(expanded)*
- Translates radar backscatter signatures into optical-equivalent semantic labels using contrastive cross-modal embeddings.
- Enables reasoning under **low-visibility conditions** (cloud cover, nighttime, smoke) where optical sensors fail but SAR remains effective.

### Module F — Orchestration / Agentic Routing Layer *(expanded)*
- A lightweight intent classifier + planner (rule-based fallback + LLM-based reasoning) that decides which module(s) a query requires.
- Supports **multi-hop tool use**, e.g., a single query may require change detection *followed by* grounding of the changed region.

### Module G — Structured Response Generator *(expanded)*
- Serializes outputs into interoperable formats: **GeoJSON, Shapefile, COCO JSON, semantic GeoTIFF, plain text, and annotated image overlays**.
- Includes a confidence score and provenance metadata (sensor ID, acquisition date, resolution) with every response for auditability.

---

## 5. System Scope

### In-Scope
- **Conversational RS-VQA** — Textual answers regarding layout patterns, land use, and object counts/types.
- **Dual-Epoch Change Analysis** — Dual raster comparisons mapping modifications between distinct timestamp intervals (T₁ vs T₂).
- **Cross-Modal Inference** — Translating text intents into radar-parameter queries for low-visibility situations (heavy cloud layers, nighttime tracking).
- **Interoperable Data Outputs** — Native conversion to standard geospatial outputs including GeoJSON, shapefiles, and custom semantic GeoTIFFs.
- **Multi-turn Dialogue** — Context retention across a conversational session for iterative refinement of queries.
- **Explainability Overlays** — Visual attention/heatmap overlays showing *why* the model produced a given answer.
- **Batch/Bulk Query Mode** — Ability to run the same query template across multiple tiles/regions for large-scale monitoring (e.g., a state-wide deforestation sweep).

### Out-of-Scope
- **Dynamic Spacecraft Command & Control** — Direct interaction with orbiters or control of sensor acquisition schedules.
- **Pure Generative Hallucination** — Creating high-resolution imagery assets over completely blind areas lacking contextual/structural markers (the system will refuse or flag low-confidence regions rather than fabricate detail).
- **Real-time Live Satellite Tasking** — The system operates on archived/downlinked imagery, not live sensor feeds requiring tasking requests.
- **Classified/Restricted Sensor Data Handling** — Outside the scope of the prototype unless explicitly cleared and sandboxed for a specific deployment.

---

## 6. Data Pipeline & Preprocessing

| Stage | Description |
|---|---|
| **Ingestion** | Pulls imagery from public/partner sources — Bhuvan (ISRO), Sentinel Hub (ESA Copernicus), Landsat (USGS), and simulated Cartosat/RISAT feeds. |
| **Radiometric Correction** | Atmospheric correction for optical bands; speckle-filtering (e.g., Lee/Frost filters) for SAR data. |
| **Geometric Correction** | Orthorectification and re-projection to a common CRS (typically EPSG:4326 or local UTM zones). |
| **Tiling** | Splits large scenes into manageable tiles (512×512 / 1024×1024) with configurable overlap for edge-artifact correction. |
| **Annotation Harmonization** | Normalizes labels across heterogeneous training datasets (RSVQA, GeoChat-Instruct, EarthGPT) into a unified instruction-tuning schema. |
| **Metadata Indexing** | Stores acquisition date, sensor type, resolution, cloud-cover percentage, and geolocation bounds in a searchable catalog (e.g., STAC-compliant catalog). |

---

## 7. Research Depth & Literature Foundation

| Domain | Core Academic References | Focus Areas |
|---|---|---|
| Vision-Language Adaptation | SkyEyeGPT (2024) — [arXiv:2401.09412](https://arxiv.org/abs/2401.09412) | Instruction tuning across multiple satellite sensor datasets. |
| Conversational Geospatial Agents | GeoChat (2023) — [arXiv:2311.15826](https://arxiv.org/abs/2311.15826) | Visual grounding, dialogue loops, and object localization benchmarks. |
| Multi-Sensor Transformers | EarthGPT (2024) — [arXiv:2401.16822](https://arxiv.org/abs/2401.16822) | Cross-attention tokens mapping multi-spectral inputs uniformly. |
| Visual Answering Groundwork | RSVQA Framework (2020) | Standardizing metrics and question formats for geospatial language models. |
| Change-Aware VQA Systems | ChangeVQA (2023) — [arXiv:2307.01452](https://arxiv.org/abs/2307.01452) | Measuring multi-temporal changes over identical geographic locations via conversational requests. |
| Promptable Segmentation | Segment Anything Model / SAM-RS adaptations | Zero-shot, prompt-driven object and boundary segmentation applied to overhead imagery. |
| Parameter-Efficient Fine-Tuning | LoRA (2021) | Low-cost adaptation of large pretrained backbones to the remote-sensing domain without full retraining. |

---

## 8. Model Training & Evaluation Strategy

### Training Approach
- **Stage 1 — Backbone Pretraining Alignment:** Freeze the base LLM; train only the vision-projection adapter on paired image-caption remote sensing data.
- **Stage 2 — Instruction Fine-Tuning:** Apply LoRA adapters across attention layers using curated instruction datasets (RSVQA, GeoChat-Instruct, EarthGPT, ChangeVQA).
- **Stage 3 — Task-Specific Heads:** Train the SAM-RS grounding head and the Siamese change-detection network jointly with the frozen multimodal backbone.
- **Stage 4 — RLHF-lite / Preference Tuning (optional):** Use analyst feedback loops to reduce hallucination and improve answer specificity.

### Evaluation Metrics
| Task | Metric(s) |
|---|---|
| RS-VQA | Accuracy, F1-score (per question type: count, presence, comparison) |
| Visual Grounding | IoU (Intersection over Union), mAP@[.5:.95] |
| Change Detection | Precision/Recall on changed-pixel masks, Kappa coefficient |
| Cross-Modal Fusion | Cross-modal retrieval accuracy (SAR ↔ Optical pairing) |
| Response Quality | BLEU/ROUGE for descriptive answers, human expert grading for factuality |
| Latency | End-to-end query response time (target: < 5s for single-tile queries) |

---

## 9. Scalability Measures

- **Dynamic Tile-Based Inference:** Massive satellite scenes (e.g., 10,000 × 10,000 pixels) are streamed dynamically as non-overlapping tiles (512×512 or 1024×1024). Predictions are stitched concurrently via edge-overlap correction networks to prevent boundary artifacts.
- **Distributed Vector Search (RAG):** Multi-modal embeddings and regional history tables are archived inside vector databases (**Milvus** or **pgvector**) to enable contextual historical memory lookups (e.g., *"has this region changed significantly in the last 5 years?"*).
- **Hardware Acceleration Pipeline:** Uses **NVIDIA Triton Inference Server** coupled with **TensorRT-LLM** optimizations (FP16/INT8 weight quantization) to maximize data processing throughput while decreasing response times.
- **Horizontal Auto-Scaling:** Containerized microservices (Kubernetes/KServe) that scale inference pods based on query load, particularly during disaster-response surge periods.
- **Caching Layer:** Frequently queried tiles/regions cached with a TTL-based invalidation policy tied to new imagery ingestion events.
- **Asynchronous Batch Queueing:** Long-running bulk/regional sweeps processed via a job queue (e.g., Celery/RabbitMQ) with progress-tracking notifications rather than blocking the chat interface.

---

## 10. Deployment & Infrastructure

| Layer | Technology Choice | Rationale |
|---|---|---|
| Compute | Kubernetes on GPU-backed nodes (A100/H100 or equivalent) | Elastic scaling for variable inference load |
| Inference Serving | NVIDIA Triton + TensorRT-LLM | High-throughput, quantized model serving |
| Vector Store | Milvus / pgvector | Fast similarity search for RAG-based historical context |
| Object/Raster Storage | Cloud object storage (S3-compatible) with COG (Cloud-Optimized GeoTIFF) support | Efficient partial-read access to massive rasters |
| API Layer | FastAPI / gRPC gateway | Low-latency, typed contract for UI and third-party GIS plugin consumption |
| Frontend | React-based web dashboard + QGIS plugin | Accessibility across both general users and GIS professionals |
| Monitoring | Prometheus + Grafana | Real-time observability of latency, GPU utilization, and error rates |

---

## 11. Security, Privacy & Compliance

- **Data Sovereignty:** Sensitive/defense-grade imagery processed within on-premises or government-approved cloud enclaves; public-domain imagery may use standard cloud infrastructure.
- **Access Control:** Role-based access control (RBAC) distinguishing public users, verified analysts, and administrative roles.
- **Audit Logging:** Every query, model version, and output is logged with provenance metadata for traceability and accountability.
- **Export Control Awareness:** High-resolution defense-relevant outputs gated behind additional authorization checks in line with national geospatial data policies.
- **Model Output Watermarking:** Generated overlays/masks tagged with a machine-readable provenance stamp to distinguish AI-derived annotations from ground-truth survey data.

---

## 12. Architecture Decision Records (ADRs)

### ADR 001: Model Backbone
- **Decision:** Pair ViT-H/14 as the image backbone alongside LLaVA-1.6-Mistral-7B for structural reasoning and interaction.
- **Consequence:** Excellent zero-shot generalization capabilities across complex terrain features, requiring minimal custom formatting for geographic datasets. Trade-off: larger compute footprint than smaller backbones, mitigated via quantization.

### ADR 002: Spatial Geometry Generation
- **Decision:** Append a downstream SAM-RS promptable segmentation module triggered by the multimodal text tokens.
- **Consequence:** Empowers the conversational system to seamlessly deliver valid vector shapes (GeoJSON) instead of being restricted to string responses. Adds an additional inference hop, slightly increasing latency for grounding-heavy queries.

### ADR 003: Cross-Modal Alignment Processing
- **Decision:** Implement cross-attention fusion matrices at the encoder phase instead of processing separate late-stage visual models.
- **Consequence:** Maximizes semantic consistency during seasonal cloud cover but slightly increases encoder-level parameter training costs.

### ADR 004: Vector Database Choice *(new)*
- **Decision:** Use Milvus/pgvector for RAG-based historical embedding storage instead of a purely relational metadata store.
- **Consequence:** Enables fast approximate nearest-neighbor search over historical scene embeddings for contextual recall, at the cost of added infrastructure complexity versus a simple SQL table.

### ADR 005: Serving Infrastructure *(new)*
- **Decision:** Standardize on NVIDIA Triton + TensorRT-LLM for all production inference rather than raw PyTorch serving.
- **Consequence:** Significant latency and throughput gains via quantization and batching, but requires model export/compilation overhead during CI/CD.

---

## 13. Risks & Mitigation Strategy

| Risk | Impact | Mitigation |
|---|---|---|
| Model hallucination on visually ambiguous regions | Incorrect operational decisions | Confidence thresholds + explicit "insufficient evidence" fallback responses |
| Sensor domain gap (SAR ↔ Optical) | Poor cross-modal grounding accuracy | Dedicated projection layer + contrastive pretraining on paired SAR-optical datasets |
| Latency on very large scenes | Poor user experience | Tile-based streaming inference + caching |
| Data drift from new sensor generations | Degraded accuracy over time | Continuous evaluation pipeline + scheduled fine-tuning cycles |
| Sensitive geospatial data misuse | Security/compliance violation | RBAC, audit logging, and export-control gating |
| Limited labeled training data for niche object classes | Weak performance on rare categories | Active learning loop with analyst-in-the-loop annotation feedback |

---

## 14. Success Metrics & KPIs

- **Query Resolution Accuracy** ≥ 85% on internal RS-VQA benchmark.
- **Change Detection F1-score** ≥ 0.80 on held-out multi-temporal test pairs.
- **Average Response Latency** < 5 seconds for single-tile queries, < 30 seconds for full-scene sweeps.
- **User Adoption:** Number of active analyst sessions per week post-deployment.
- **Reduction in Manual Annotation Time:** Target 60–70% reduction compared to traditional GIS workflows.

---

## 15. Implementation Roadmap

| Phase | Duration (indicative) | Deliverables |
|---|---|---|
| Phase 1 — Data & Baseline | 4–6 weeks | Curated multi-sensor dataset, baseline VQA model fine-tuned |
| Phase 2 — Grounding & Segmentation | 4 weeks | SAM-RS integration, GeoJSON output pipeline |
| Phase 3 — Change Detection & Fusion | 5 weeks | Siamese change network, SAR-optical cross-modal layer |
| Phase 4 — Orchestration & UI | 3 weeks | Agentic router, web dashboard, QGIS plugin prototype |
| Phase 5 — Scaling & Hardening | 3 weeks | Triton/TensorRT deployment, caching, monitoring dashboards |
| Phase 6 — Pilot & Feedback | Ongoing | Analyst pilot testing, feedback-driven fine-tuning |

---

## 16. Team & Skill Requirements

- **ML/Vision-Language Engineers** — model fine-tuning, PEFT/LoRA, multimodal fusion.
- **Remote Sensing Domain Experts** — SAR/optical interpretation, radiometric/geometric correction know-how.
- **Backend/Infra Engineers** — Kubernetes, Triton, vector databases.
- **Frontend/GIS Engineers** — React dashboard, QGIS plugin development.
- **Data Engineers** — ingestion pipelines, STAC catalog management, annotation harmonization.
- **QA/Evaluation Specialists** — benchmark design, hallucination auditing, human-in-the-loop review.

---

## 17. Future Enhancements

- **3D Terrain Reasoning:** Fusing DEM (Digital Elevation Model) data for volumetric queries (e.g., landslide volume estimation).
- **Voice-Based Query Interface:** Enabling field analysts to query imagery hands-free.
- **Federated Fine-Tuning:** Allowing partner agencies to fine-tune locally on sensitive data without centralizing raw imagery.
- **Automated Report Generation:** One-click conversion of a conversational session into a formatted PDF/DOCX situational report.
- **Edge Deployment:** Lightweight quantized model variants for on-board or field-station inference where connectivity is limited.

---

## 18. Glossary

| Term | Definition |
|---|---|
| **SAR** | Synthetic Aperture Radar — an active remote sensing technique unaffected by cloud cover or darkness. |
| **RS-VQA** | Remote Sensing Visual Question Answering — answering natural language questions about satellite imagery. |
| **PEFT/LoRA** | Parameter-Efficient Fine-Tuning / Low-Rank Adaptation — techniques to fine-tune large models cheaply. |
| **GeoJSON** | An open standard format for encoding geographic data structures using JSON. |
| **COG** | Cloud-Optimized GeoTIFF — a raster format enabling efficient partial reads over HTTP. |
| **STAC** | SpatioTemporal Asset Catalog — a standardized way to index geospatial data. |
| **ViT** | Vision Transformer — a transformer-based architecture for image encoding. |
| **RAG** | Retrieval-Augmented Generation — augmenting model responses with retrieved external context. |

---

*This document is a living solution architecture for SatQuery AI (SIH 167) and is intended to evolve alongside prototype development, pilot feedback, and evaluation results.*
