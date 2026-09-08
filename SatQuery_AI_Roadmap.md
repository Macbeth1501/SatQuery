# SatQuery AI (SIH26167) - Project Roadmap

## Overview
This roadmap outlines the development lifecycle for **SatQuery AI**, an agentic vision-language assistant for analyzing remote-sensing images. The timeline prioritizes the solution design and presentation delivery by September 14, followed directly by implementation and MVP prototyping.

## Timeline Table

| Date | Phase | Key Tasks |
| :--- | :--- | :--- |
| **Sept 8** | Phase 1: Research | Problem Statement Understanding |
| **Sept 9** | Phase 1: Research | Literature Review & GitHub Recon (BigEarthNet paper) |
| **Sept 10** | Phase 1: Research | Dataset Exploration (BigEarthNet, VRSBench, RSVQA, CDVQA) |
| **Sept 11** | Phase 2: Design | Architecture Mapping (Agentic Controller & Tool Registries) |
| **Sept 12** | Phase 2: Design | Proposed Solution Documentation |
| **Sept 13** | Phase 2: Design | PPT Development (Drafting execution traces & novelty) |
| **Sept 14** | Phase 2: Design | **PPT Finalization & Submission Deadline** |
| **Sept 15-25** | Phase 3: Build | Core Orchestration & Task Routing Implementation |
| **Sept 26-Oct 5** | Phase 3: Build | Model Fine-Tuning (Remote-sensing adaptation) |
| **Oct 6-12** | Phase 3: Build | Frontend GUI Development (Interactive Web App) |
| **Oct 13+** | Phase 3: Build | MVP Prototyping, Benchmarking & Evaluation |

---

## Detailed Phase Breakdown

### Phase 1: Research & Conceptualization (Sept 8–10)
*   **PS Understanding (Sept 8):** Deconstruct the ISRO requirements for developing an agentic vision-language assistant capable of analyzing single and paired remote-sensing images. 
*   **Literature & GitHub Recon (Sept 9):** Analyze the provided BigEarthNet paper (arxiv: 2603.29630) and scout GitHub repositories for open-source remote-sensing specialist models (VQA, captioning, grounding). 
*   **Dataset Exploration (Sept 10):** Review the structures of BigEarthNet.txt, VRSBench, RSVQA, and CDVQA to understand the training and evaluation formatting for visual question answering and captioning tasks.

### Phase 2: Solution Design & PPT Delivery (Sept 11–14)
*   **Architecture Mapping (Sept 11):** Design the agentic controller responsible for query interpretation, input validation, and model selection. Leverage existing knowledge of hybrid deep learning architectures for satellite imagery to structure the cross-modal pipelines efficiently.
*   **Proposed Solution (Sept 12):** Detail the interactive web application backend that integrates task routing, spatial output combinations, and confidence estimation. 
*   **PPT Development (Sept 13–14):** Draft the presentation highlighting the system's novelty as a query-driven framework rather than a generic, unadapted LLM. Ensure the slides clearly illustrate the execution trace generation before submitting on **September 14th**. 

### Phase 3: Implementation & MVP Prototyping (Sept 15 Onwards)
*   **Core Orchestration (Sept 15–25):** Build the task planning backend utilizing PyTorch frameworks to handle automated tool execution, model sequencing, and output integration.
*   **Model Fine-Tuning (Sept 26–Oct 5):** Adapt the primary visual components to domain-specific remote-sensing terminology using BigEarthNet.txt.
*   **Frontend GUI (Oct 6–12):** Develop the user interface to accept natural language queries and support required formats like GeoTIFF, TIFF, PNG, and JPEG.
*   **Testing & Evaluation (Oct 13+):** Benchmark the MVP against single-image VQA and multitemporal change analysis criteria to prepare for the undisclosed ISRO/SAC evaluation dataset.
