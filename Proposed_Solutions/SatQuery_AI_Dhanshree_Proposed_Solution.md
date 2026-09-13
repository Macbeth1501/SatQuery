# SatQuery AI --- Research-Driven Proposed Solution for SIH 2026 PS-167

**Problem Statement:** SatQuery AI --- An Interactive Vision-Language
Assistant for Multimodal Remote Sensing Image Analysis through Text
Queries\
**Organizations:** ISRO / DRDO\
**Category:** Software

## 1. Executive Summary

SatQuery AI should not be another remote-sensing chatbot. It should be
an evidence-driven agentic Remote-Sensing Intelligence System that
dynamically interprets a natural-language query, determines which
sensor(s), temporal relationship and specialist models are required,
executes them, cross-validates their outputs, and produces an answer
together with visual evidence, confidence and an auditable execution
trace.

### Core shift

**Existing approach:** Image → VLM → Answer

**Proposed SatQuery:** User Query → Query Understanding →
Task/Sensor/Time Planner → Specialist Models → Evidence Fusion →
Confidence/Validation → Grounded Answer + Visual Evidence + Execution
Trace.

------------------------------------------------------------------------

## 2. Research Landscape

### BigEarthNet.txt

BigEarthNet.txt provides large-scale multisensor image-text supervision
for Sentinel-1/Sentinel-2, including VQA and referring-expression tasks.
It is useful for remote-sensing domain adaptation.

### EarthDial

EarthDial advances interactive dialogue over multisensory, multitemporal
and multimodal Earth observations.

### GeoChat

GeoChat demonstrates grounded remote-sensing vision-language interaction
with image- and region-level understanding.

### Change Detection Meets VQA

This work establishes change-based visual question answering over
bi-temporal remote-sensing observations.

### MM-OVSeg

MM-OVSeg demonstrates optical-SAR fusion for open-vocabulary
segmentation and complementary sensor reasoning.

### REBEN

REBEN provides a refined Sentinel-1/Sentinel-2 benchmark useful for
multimodal remote-sensing analysis.

### Revisiting Change VQA with Qwen

This recent work demonstrates the relevance of modern native multimodal
models for change reasoning and shows that larger models do not
automatically guarantee better results.

### RS-LLaVA

RS-LLaVA combines remote-sensing captioning and question answering using
an adapted LLaVA architecture.

### Vision-Language Models in Remote Sensing

The review provides the broader research landscape, limitations and
future directions.

### VRSBench

VRSBench provides broad evaluation resources for remote-sensing
captioning, grounding and VQA.

------------------------------------------------------------------------

## 3. Central Research Gap

Existing research largely focuses on **building better individual
models**. PS-167 requires a system capable of **intelligently using
multiple models and tools** according to a user's query.

### Key opportunity

-   Specialist model selection
-   Automatic task decomposition
-   Dynamic tool chaining
-   Cross-validation of model outputs
-   Query-dependent sensor selection
-   Evidence-backed answers
-   Auditable execution traces

------------------------------------------------------------------------

## 4. Proposed Solution --- Agentic Earth Observation Intelligence Layer

SatQuery AI is an **agentic orchestration platform**.

The user supplies a natural-language query and one or more observations.
The system:

1.  Interprets intent
2.  Validates inputs
3.  Selects specialists from a predefined registry
4.  Executes the required workflow
5.  Fuses evidence
6.  Generates a grounded response

------------------------------------------------------------------------

## 5. Query-to-Evidence Pipeline

``` text
USER
  ↓
QUERY UNDERSTANDING
  ↓
OBSERVATION PARSER
  ↓
TASK / AGENTIC ROUTER
  ↓
VQA / GROUNDING / CAPTIONING / CHANGE / SEGMENTATION / OPTICAL-SAR
  ↓
EVIDENCE FUSION
  ↓
CONFIDENCE + VALIDATION
  ↓
GROUNDED RESPONSE
  ↓
VISUAL EVIDENCE + AUDIT TRACE
```

------------------------------------------------------------------------

## 6. Agentic Architecture

### Query Understanding Agent

Converts natural language into structured intent such as:

-   Task
-   Target object
-   Temporal requirement
-   Localization requirement

Example:

``` json
{
  "task": "change_vqa",
  "target": "built_up_area",
  "temporal": true,
  "requires_localization": true
}
```

### Input Validation Agent

Checks:

-   Number of images
-   Format
-   Sensor modality
-   Temporal relationship
-   Spatial compatibility
-   Resolution
-   Co-registration
-   Metadata

### Specialist Router

Maintains a predefined model/tool registry:

``` text
VQA
 └── RS-VQA model

CAPTIONING
 └── RS-LLaVA / adapted VLM

GROUNDING
 └── GeoChat-style grounding

CHANGE VQA
 └── Change-VQA specialist

CHANGE MAP
 └── Change Detection model

OPTICAL-SAR
 └── Multimodal fusion model

SEGMENTATION
 └── Open-vocabulary segmentation

REASONING
 └── Remote-sensing VLM
```

### Evidence Fusion Agent

Combines:

-   Text outputs
-   Masks
-   Regions
-   Change maps
-   Sensor-specific outputs

### Confidence / Validation Agent

Estimates confidence from evidence quality and agreement rather than
relying only on an LLM-generated confidence value.

------------------------------------------------------------------------

## 7. Key Innovation #1 --- Evidence Graph

Instead of allowing the final language model to freely generate an
answer from raw images, SatQuery constructs an **Evidence Graph**
linking the user question to model outputs, spatial regions,
classifications, change measurements and final conclusions.

Example:

``` text
User Question
      ↓
Change Detector
      ↓
Changed Regions
      ↓
Built-up Classifier
      ↓
Area Estimator
      ↓
Temporal Evidence
      ↓
Final Answer
```

------------------------------------------------------------------------

## 8. Key Innovation #2 --- Evidence Triangulation

Important answers can be supported by multiple independent evidence
sources:

**Optical evidence + SAR evidence + segmentation + change-map evidence**

Agreement raises confidence. Disagreement triggers an uncertainty-aware
response.

------------------------------------------------------------------------

## 9. Key Innovation #3 --- Sensor-Adaptive Reasoning

The system does not always use every available sensor. It selects
sensors according to the information requested.

Examples:

-   Multispectral data → spectral/vegetation questions
-   SAR → structural and cloud-resilient analysis
-   Optical + SAR → complementary information
-   T1 + T2 → temporal analysis

This makes the system **query-driven rather than sensor-driven**.

------------------------------------------------------------------------

## 10. Key Innovation #4 --- Contradiction-Aware Agent

If specialist outputs disagree, SatQuery should not force a confident
answer.

Example:

``` text
Optical:
Built-up = 0.81

SAR:
Built-up = 0.34

Segmentation:
Built-up = 0.45

Agreement:
LOW
```

The system can respond:

> The evidence is inconclusive. Optical imagery indicates built-up land,
> while SAR-based structural evidence is weaker.

------------------------------------------------------------------------

## 11. Key Innovation #5 --- Active Evidence Acquisition

When a requested conclusion requires missing evidence, the system can
identify what additional observation would improve confidence.

Example:

> SAR imagery for the earlier date would improve confidence in this
> comparison.

This creates an **evidence-aware assistant** rather than a
hallucination-prone chatbot.

------------------------------------------------------------------------

## 12. Key Innovation #6 --- Explainable Execution Trace

The UI should visibly show:

``` text
EXECUTION TRACE

✓ Input validation
  2 images detected

✓ Temporal relationship
  T1 → T2

✓ Query classification
  Change + built-up analysis

✓ Selected tools
  Change Detection
  Built-up Segmentation
  Temporal Reasoning

✓ Evidence
  3 significant changed regions

✓ Cross-validation
  Optical + SAR agreement

✓ Final confidence
  High
```

This directly supports the PS requirement for an auditable execution
summary.

------------------------------------------------------------------------

## 13. Example --- Cross-Modal Query

**Query:**

> Use the optical and SAR images together to identify built-up and
> water-covered regions.

### Workflow

``` text
Query Understanding
        ↓
Optical/SAR Compatibility Check
        ↓
Optical-SAR Fusion
        ↓
Open-Vocabulary Segmentation
        ↓
Region Extraction
        ↓
Evidence Fusion
        ↓
Visual Overlay + Answer + Confidence
```

------------------------------------------------------------------------

## 14. Example --- Bi-Temporal Query

**Query:**

> Has the built-up area increased, decreased, or remained unchanged?

### Workflow

``` text
T1 + T2 Compatibility
        ↓
Change Detection
        ↓
Built-up Segmentation
        ↓
Area Calculation
        ↓
Temporal Comparison
        ↓
Evidence-backed Conclusion
        ↓
Change Visualization
```

------------------------------------------------------------------------

## 15. Dataset Strategy

### BigEarthNet.txt

Primary domain-adaptation resource for:

-   Multisensor image-text learning
-   VQA
-   Grounding
-   Remote-sensing terminology

### VRSBench

For:

-   Captioning
-   Grounding
-   VQA evaluation

### REBEN

For:

-   Sentinel-1/Sentinel-2 multimodal representation
-   Segmentation/classification
-   Sensor fusion experiments

### CDVQA

For:

-   Bi-temporal change reasoning
-   Change-VQA

### ISRO/SAC Evaluation Dataset

Final target evaluation, including co-registered Cartosat-2S optical and
RISAT SAR pairs as specified by the PS.

------------------------------------------------------------------------

## 16. Suggested Technology Stack

  Layer            Technology
  ---------------- ----------------------------------------------------
  Frontend         React + Tailwind CSS
  Backend          Python + FastAPI
  Agent            Python orchestration layer
  ML               PyTorch
  Remote Sensing   Rasterio, GDAL, OpenCV, NumPy
  Visualization    Image overlays, masks, bounding boxes, change maps
  Storage          Local/Object Storage

------------------------------------------------------------------------

## 17. What Not to Build

-   Do not build only a generic chatbot.
-   Do not train one enormous model from scratch.
-   Do not manually select models for every query.
-   Do not make change detection the entire project.
-   Do not claim unsupported causal explanations from imagery.

------------------------------------------------------------------------

## 18. Research-to-Innovation Matrix

  -----------------------------------------------------------------------
  Research                What we take            What we add
  ----------------------- ----------------------- -----------------------
  BigEarthNet.txt         S1/S2 image-text        Query-driven model
                          learning                selection

  GeoChat                 Grounding               Grounding as an agent
                                                  tool

  EarthDial               Multisensor dialogue    Explicit orchestration

  RS-LLaVA                Captioning + VQA        Specialist routing

  CDVQA                   Temporal reasoning      Evidence graph

  Qwen Change-VQA         Modern multimodal       Model selection based
                          reasoning               on task

  MM-OVSeg                Optical-SAR fusion      Fusion as
                                                  query-triggered tool

  REBEN                   Better S1/S2 training   Multimodal evidence
                                                  validation

  VRSBench                VQA/grounding/caption   Multi-task evaluation
                          benchmark               
  -----------------------------------------------------------------------

------------------------------------------------------------------------

## 19. Hackathon MVP

### Single Image

-   Upload image
-   VQA
-   Captioning
-   Grounding

### Two Images

-   Change detection
-   Change VQA
-   Change visualization

### Optical + SAR

-   Basic fusion
-   Built-up/water identification

### Agent

-   Query classification
-   Input validation
-   Tool selection
-   Execution trace

### Advanced

-   Evidence graph
-   Contradiction detection
-   Confidence calibration
-   Active evidence acquisition

------------------------------------------------------------------------

## 20. Demo Strategy

### Demo 1 --- Single Image

> Describe this scene and identify major objects.

Output:

**Caption + answer + regions**

### Demo 2 --- Grounding

> Where is the water body?

Output:

**Grounded highlighted region**

### Demo 3 --- Cross-Modal

> Use optical and SAR to identify built-up areas.

Output:

**Optical + SAR fused evidence**

### Demo 4 --- Temporal

> What changed between these dates?

Output:

**T1 → T2 → change map → explanation**

### Demo 5 --- Complex Query

> Has urban development increased, and where is the strongest evidence?

Workflow:

``` text
Query Decomposition
       ↓
Change Detection
       +
Built-up Segmentation
       +
Optical-SAR Analysis
       ↓
Evidence Fusion
       ↓
Spatial Visualization
       ↓
Natural-Language Answer
       +
Confidence
       +
Execution Trace
```

------------------------------------------------------------------------

## 21. Final Winning Positioning

### Do not pitch

> AI chatbot for satellite images.

### Pitch

# An Agentic Evidence Engine for Earth Observation

### One-line pitch

> **SatQuery AI turns satellite imagery into an evidence-backed
> conversation by letting an agent dynamically choose the right sensors,
> models and analysis tools for every question.**

### 30-second pitch

SatQuery AI is an agentic Vision-Language assistant for remote sensing.
Instead of relying on one generic VLM, it understands the user's
question, validates available observations, dynamically selects
specialist models for VQA, grounding, change detection, segmentation and
optical-SAR fusion, and combines their outputs into an evidence-grounded
answer. Every response includes visual evidence, confidence and an
auditable execution trace, making the system not only conversational but
also explainable and trustworthy for real-world Earth observation
analysis.

------------------------------------------------------------------------

## 22. Final Architecture

``` text
                       ┌─────────────────────┐
                       │       USER          │
                       │ Natural Language    │
                       │       Query         │
                       └──────────┬──────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │   QUERY UNDERSTANDING   │
                    │ Intent + Objects + Time │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   INPUT VALIDATION      │
                    │ Sensor / Format / Time  │
                    │ Co-registration / Meta  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │    AGENTIC PLANNER      │
                    │   TASK DECOMPOSITION    │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
        ┌───────────┐      ┌───────────┐      ┌───────────┐
        │    VQA    │      │ GROUNDING │      │  CHANGE   │
        │ Specialist│      │ Specialist│      │ Specialist│
        └─────┬─────┘      └─────┬─────┘      └─────┬─────┘
              │                  │                  │
              ▼                  ▼                  ▼
        ┌───────────┐      ┌───────────┐      ┌───────────┐
        │ CAPTION   │      │SEGMENTATION│     │ TEMPORAL  │
        │ Specialist│      │ Specialist │     │ REASONING │
        └─────┬─────┘      └─────┬─────┘      └─────┬─────┘
              │                  │                  │
              └──────────────────┼──────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  OPTICAL + SAR FUSION   │
                    │   Cross-modal Evidence  │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │    EVIDENCE GRAPH       │
                    │ + CONTRADICTION CHECK   │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ CONFIDENCE / VALIDATION │
                    └────────────┬────────────┘
                                 │
                     ┌───────────┴───────────┐
                     ▼                       ▼
             ┌───────────────┐       ┌───────────────┐
             │   GROUNDED    │       │    AUDIT      │
             │    ANSWER     │       │    TRACE      │
             └───────┬───────┘       └───────────────┘
                     │
                     ▼
             ┌─────────────────┐
             │ VISUAL EVIDENCE │
             │ Maps / Boxes /  │
             │ Masks / Overlays │
             └─────────────────┘
```

------------------------------------------------------------------------

## 23. Final Recommendation

The team should **not** pitch SatQuery as "an AI chatbot for satellite
images."

The stronger positioning is:

> **An Agentic Evidence Engine for Earth Observation.**

The three strongest differentiators are:

1.  **Query-to-Tool Intelligence** --- the system decides what analysis
    needs to happen.
2.  **Evidence Triangulation** --- the system combines multiple
    specialist outputs and sensors instead of trusting one VLM.
3.  **Auditable Grounded Answers** --- every answer is accompanied by
    visual evidence, confidence and execution trace.

### Final research-to-solution story

``` text
Existing Research
      ↓
Better RS VLMs
      ↓
Multimodal EO Models
      ↓
Change / Grounding / Fusion
      ↓
        GAP
   "Who coordinates them?"
      ↓
   SATQUERY AI
      ↓
Agentic Orchestration
      +
Evidence Triangulation
      +
Grounded Response
      +
Auditability
```

------------------------------------------------------------------------

## Research Sources

-   BigEarthNet.txt --- https://txt.bigearth.net/
-   EarthDial --- CVPR 2025
-   GeoChat --- CVPR 2024
-   Change Detection Meets VQA --- https://arxiv.org/abs/2112.06343
-   MM-OVSeg --- https://arxiv.org/abs/2603.17528
-   VRSBench --- NeurIPS 2024
-   REBEN --- https://arxiv.org/abs/2407.03653
-   RS-LLaVA --- Remote Sensing
-   Vision-Language Models in Remote Sensing --- Review
-   Revisiting Change VQA with Structured and Native Multimodal Qwen
    Models --- https://arxiv.org/abs/2604.18429

------------------------------------------------------------------------

*Prepared as a research-driven proposed solution for SIH 2026 PS-167.*
