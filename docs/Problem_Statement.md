# SIH26167 — SatQuery AI

## Problem Statement

**SIH26167: SatQuery AI - An Interactive Vision-Language Assistant for Multimodal Remote Sensing Image Analysis through Text Queries**

**Organization:** Indian Space Research Organisation (ISRO)  
**Department:** Department of Space / Indian Space Research Organisation

---

## Dataset

**Training / Fine-Tuning Dataset:** `BigEarthNet.txt`

BigEarthNet.txt is the primary dataset for remote-sensing adaptation using co-registered Sentinel-1 SAR, Sentinel-2 multispectral imagery, and diverse text annotations.

**Dataset / Paper:** https://arxiv.org/abs/2603.29630

All datasets are available online and are open source.

### Public Evaluation Benchmarks

- **VRSBench** — for remote-sensing visual understanding tasks including captioning, grounding, and related evaluation.
- **RSVQA** — for single-image visual question answering.
- **CDVQA** — for multitemporal change-based visual question answering.

---

# Background

Remote-sensing imagery is widely used for agricultural monitoring, disaster management, urban planning, forest monitoring, water-resource assessment, infrastructure mapping, and environmental analysis. However, most existing remote-sensing AI solutions are developed as isolated applications for a single predefined task, such as land-cover classification, object detection, visual question answering, or change detection.

These systems often require users to understand satellite-data characteristics, GIS workflows, model selection, and task-specific parameters. Consequently, non-expert users may find it difficult to obtain meaningful information from satellite imagery through simple natural-language queries.

Many operational remote-sensing questions cannot always be answered reliably using a single optical image. Relevant information may be distributed across paired or multiple observations acquired at different times or by different sensors.

Optical and multispectral imagery provides spectral and contextual information, whereas Synthetic Aperture Radar (SAR) provides complementary structural information and supports day-and-night acquisition through cloud cover. Multitemporal image pairs are required to identify and interpret changes over time, while co-registered optical-SAR pairs can provide more complete and reliable information than either modality alone.

A general-purpose Large Language Model (LLM) or Vision-Language Model (VLM) cannot be expected to perform these specialised tasks reliably without adaptation to remote-sensing imagery, sensor characteristics, and domain-specific terminology.

The proposed solution must therefore include remote-sensing fine-tuning or domain adaptation and may employ multiple specialised models for different tasks.

**BigEarthNet.txt** will serve as the primary dataset for adapting image-text representations to multisensor remote-sensing data. **VRSBench** and **RSVQA** will be used to evaluate single-image captioning, grounding, and visual question answering, while **CDVQA** will be used to evaluate multitemporal change-based visual question answering.

The novelty of **SatQuery AI** lies in its agentic, query-driven framework. Instead of applying a single generic VLM, the system selects and executes suitable remote-sensing specialist models, validates inputs, combines their outputs, and returns an evidence-grounded response.

---

# Description

The objective is to develop **SatQuery AI**, a software-based agentic vision-language assistant for analysing single and paired remote-sensing images through natural-language queries.

Single-image understanding is a mandatory baseline, while the principal focus is joint reasoning over paired cross-modal and multitemporal imagery.

---

# Defined Input Scope

### 1. Single Image

One optical/multispectral or SAR image for:

- Captioning
- Visual Question Answering (VQA)
- Text-guided region grounding

### 2. Cross-Modal Pair

Co-registered optical/multispectral and SAR images of the same geographic area for:

- Joint information extraction
- Cross-modal analysis
- Complementary information understanding

### 3. Bi-Temporal Pair

Two spatially corresponding images of the same geographic area acquired at different times for:

- Change detection
- Change description
- Change-based Visual Question Answering

### 4. Supported Formats

- GeoTIFF
- TIFF
- PNG and JPEG only for the prescribed public benchmark datasets

---

# Mandatory Functional Scope

## Remote-Sensing Adaptation

At least one visual or vision-language component must be fine-tuned or otherwise adapted using **BigEarthNet.txt** or other open-source training data.

## Single-Image Baseline

Visual Question Answering is mandatory.

Each solution must additionally implement at least one of:

- Captioning / scene description
- Text-guided region grounding

## Multi-Image Change Analysis

The system must support:

- Change description, or
- Change-based Visual Question Answering

from a bi-temporal image pair.

A spatial change map may also be generated where reference masks are available.

## Cross-Modal Pair Analysis

The system must extract complementary information from a co-registered optical/multispectral and SAR image pair.

## Agentic Orchestration

The system must automatically:

1. Select the appropriate specialist models or tools.
2. Sequence the required operations.
3. Execute the selected workflow according to the query and input configuration.
4. Combine the generated outputs into an evidence-grounded response.

---

# Representative Queries

The system should be capable of handling natural-language queries such as:

- **"Describe the land-cover and major objects visible in this image."**
- **"Highlight the water body referred to in the query."**
- **"What changed between these two dates, and where did the change occur?"**
- **"Use the optical and SAR images together to identify built-up and water-covered regions."**
- **"Has the built-up area increased, decreased, or remained unchanged?"**

---

# Agentic Model and Tool Orchestration

The system may use multiple specialised components, such as:

- Remote-sensing VQA model
- Remote-sensing image captioning model
- Text-guided grounding model
- Change-understanding model
- Change-VQA model
- Optical-SAR fusion model
- Multimodal information-extraction model

The agentic controller should perform the following operations:

1. **Interpret the query and classify the requested task.**
2. **Validate the input**, including:
   - Number of images
   - Modality
   - File format
   - Metadata
   - Image compatibility
3. **Select one or more models/tools** from a predefined registry.
4. **Configure only permitted task parameters.**
5. **Execute the selected workflow.**
6. **Combine textual and spatial outputs.**
7. **Estimate confidence.**
8. **Return visual evidence.**
9. **Generate an auditable execution summary** containing:
   - Selected task
   - Model/tool names
   - Key parameters
   - Outputs

The controller may perform internal task planning. However, only the observable execution trace, including the selected task, models or tools, permitted parameters, and outputs will be evaluated.

Internal reasoning text is neither required nor evaluated.

---

# Expected Solution

The expected solution is an **interactive GUI or web application with an agentic remote-sensing AI backend**.

The system should:

1. Accept supported remote-sensing image inputs.
2. Accept natural-language queries.
3. Automatically determine the required task.
4. Select the appropriate specialist workflow.
5. Execute the required remote-sensing models/tools.
6. Return evidence-grounded textual and visual results.

The solution should include:

- Input upload and compatibility checking
- A remote-sensing-adapted vision-language component
- Specialist tools for:
  - VQA
  - Captioning or grounding
  - Change understanding
  - Optical-SAR analysis
- An agentic controller for:
  - Task routing
  - Tool execution
  - Output integration
- Visual evidence
- Confidence information
- Execution summaries
- Downloadable reports

Each solution must demonstrate:

- Single-image VQA
- One additional single-image task
- Multitemporal change understanding
- Optical-SAR paired-image analysis
- Agentic model/tool orchestration

A generic LLM or VLM without remote-sensing adaptation will **not** satisfy the requirements.

---

# Deliverables

The project must provide:

- An interactive GUI or web application
- An agentic remote-sensing AI backend
- Source code
- Models and model configuration
- Testing implementation
- Demonstration of the required functionalities

---

# Implementation Scope

The system shall support:

- Single optical/multispectral images
- Single SAR images
- Co-registered optical-SAR pairs
- Bi-temporal image pairs
- GeoTIFF/TIFF inputs
- Approved benchmark formats

The system must perform:

- Single-image Visual Question Answering
- At least one additional single-image task
- Multitemporal change analysis
- Optical-SAR joint analysis
- Agentic model/tool selection
- Interactive query-driven analysis through a GUI or web application

---

# Evaluation / Judging Criteria

Final evaluation will use prescribed public benchmark test subsets and an **ISRO/SAC evaluation dataset**. Scores will be normalised before combining different metrics.

| Evaluation Area | Evaluation Criteria |
|---|---|
| **Single-Image VQA** | Accuracy and quality of answers to questions about individual remote-sensing images |
| **Image Captioning / Scene Description** | Quality and relevance of generated descriptions of remote-sensing scenes |
| **Region Grounding** | Accuracy of text-guided spatial localisation where implemented |
| **Multitemporal Change Analysis** | Correct identification and description of changes between two observations |
| **Change-Based VQA** | Accuracy of answers to questions involving temporal changes |
| **Optical-SAR Analysis** | Ability to combine complementary information from co-registered optical and SAR imagery |
| **Remote-Sensing Adaptation** | Evidence that at least one visual/VLM component has been fine-tuned or adapted for remote-sensing data |
| **Agentic Orchestration** | Correct selection, sequencing, and execution of specialist models/tools based on the query and input configuration |
| **Input Validation** | Correct handling of image count, modality, format, metadata, and compatibility |
| **Evidence & Visual Output** | Quality of visual evidence, spatial outputs, and confidence information |
| **Execution Trace** | Clarity and auditability of selected task, models/tools, parameters, and outputs |
| **Overall System Performance** | Robustness, usability, response quality, and integration of all mandatory functionalities |

### ISRO/SAC Evaluation Dataset

The ISRO/SAC evaluation set will contain:

- Pre-georeferenced imagery
- Co-registered **Cartosat-2S optical** and **RISAT SAR** image pairs
- Task-specific reference answers
- Labels
- Bounding boxes
- Masks, where applicable

Evaluation annotations will **not** be disclosed to participating teams.

---

# Key Novelty

SatQuery AI is designed as an **agentic, query-driven remote-sensing intelligence system** rather than a single-purpose remote-sensing model.

The core novelty is the ability to:

**Natural-Language Query → Task Understanding → Input Validation → Specialist Model Selection → Multimodal/Multitemporal Analysis → Evidence Fusion → Grounded Response**

This enables users to interact with complex remote-sensing data using natural language without requiring detailed knowledge of individual satellite sensors, GIS workflows, or machine-learning models.

---

# Core Requirements Summary

| Requirement | Mandatory |
|---|---|
| Interactive GUI / Web Application | Yes |
| Natural-Language Queries | Yes |
| Remote-Sensing Model Adaptation | Yes |
| BigEarthNet.txt / Open Training Data | Yes |
| Single-Image VQA | Yes |
| Captioning or Grounding | Yes |
| Bi-Temporal Change Analysis | Yes |
| Optical-SAR Pair Analysis | Yes |
| Agentic Model/Tool Orchestration | Yes |
| Visual Evidence | Yes |
| Confidence Information | Yes |
| Execution Summary / Audit Trace | Yes |
| Downloadable Reports | Expected |
| Generic Unadapted LLM/VLM Only | Not acceptable |
