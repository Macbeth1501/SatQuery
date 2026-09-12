# GeoChat: Grounded Large Vision-Language Model for Remote Sensing

## Overview

GeoChat is a versatile, large vision-language model (VLM) specifically designed for remote sensing (RS) imagery. It provides multitask conversational capabilities, allowing it to process high-resolution RS images, answer image-level queries, and engage in region-specific dialogue based on user-provided region inputs. Furthermore, it has the unique ability to visually ground objects in its text responses by explicitly providing their precise spatial coordinates.

## Main USP (Unique Selling Proposition)

GeoChat is the first grounded Large Vision-Language Model specifically tailored for remote sensing. Unlike traditional RS models that perform narrow tasks or general VLMs that lack domain specificity, GeoChat unifies image-level and region-level reasoning within a single conversational pipeline, enabling natural language interactions interleaved with precise object localization.

## Advantages

* **Domain Specificity:** General-domain VLMs often provide inaccurate or fabricated information when interpreting RS imagery due to the domain's unique characteristics, such as diverse scale changes and an abundance of small objects. GeoChat overcomes this by utilizing RS-specific training data and adapted visual encoders.


* **Unified Multitask Capability:** It seamlessly switches between tasks like image and region captioning, visual question answering (VQA), scene classification, referring object detection, and visually grounded conversations without needing task-specific finetuning.


* **High-Resolution Processing:** It interpolates positional encodings to process higher-resolution inputs ($504\times504$ compared to standard $336\times336$), enabling better detection of small objects typical in aerial imagery.



## Key Contributions

* **RS Multimodal Instruction Dataset:** The authors developed a novel pipeline to generate a comprehensive dataset containing 318k high-quality multimodal instruction-following image-text pairs. This was achieved by extending existing RS datasets using automated descriptive pipelines and the Vicuna-v1.5 language model.


* **GeoChat Model:** By finetuning the LLaVA-1.5 architecture with their novel dataset using Low-Rank Adaptation (LoRA), the authors created a model that retains generic conversational abilities while extending its knowledge to the remote sensing domain.


* **Evaluation Benchmark:** The paper establishes comprehensive evaluation protocols to assess RS multitask conversations and visually grounded reasoning, addressing a significant benchmark gap in the field.



## Dataset

* The training dataset consists of nearly 318k multimodal instruction pairs.


* It aggregates data from multiple existing RS datasets to ensure diversity: object detection (DOTA, DIOR, FAIR1M), scene classification (NWPU-RESISC-45), and VQA (LRBEN, Floodnet).


* To address missing critical object classes (e.g., buildings, roads, trees) in the base datasets, the authors employed pseudo-labeling using a pre-trained VITAE-RVSA model.



## Methodology

* The model utilizes specific task tokens (e.g., `[grounding]`, `[identify]`, `[refer]`) in user prompts to seamlessly direct the model's behavior toward grounded conversation, region captioning, or referring expression comprehension.


* Spatial locations are represented textually as normalized bounding box coordinates, allowing the model to accept visual region prompts and output localized predictions.


* The LLM was instructed using carefully crafted templates to generate multi-round question-and-answer pairs based on extracted object attributes (category, color, relative size, location) and spatial relationships (e.g., "surrounded by", "anchored at").



## Architecture

GeoChat builds upon the LLaVA-v1.5 architecture, comprising three main components:

* **Visual Backbone:** A pre-trained CLIP-ViT(L-14) encoder. The positional encodings are interpolated to support $504\times504$ input resolutions, yielding 1296 patches per image to capture finer details.


* **MLP Cross-modal Adaptor:** A two-layer Multi-Layer Perceptron (MLP) with a GeLU activation function projects the 1024-dimensional visual tokens into the 4096-dimensional language model space.


* **Large Language Model:** The open-source Vicuna-v1.5 (7B) LLM is used to interpret user instructions, process visual features, and generate textual and spatial responses. The LLM is fine-tuned using LoRA to ensure efficient training and prevent the catastrophic forgetting of its foundational general knowledge.



## Experimental Results

* **Scene Classification:** In zero-shot settings, GeoChat significantly outperformed general VLMs, achieving an accuracy of 84.43% on the UCMerced dataset and 72.03% on the AID dataset.


* **Visual Question Answering (VQA):** On the high-resolution RSVQA-HRBEN dataset, GeoChat outperformed zero-shot generic VLMs with a 72.30% average accuracy. It also performed competitively against fully supervised, task-specific models (like RSGPT) on the RSVQA-LRBEN dataset.


* **Visual Grounding:** Evaluated on a newly proposed benchmark, GeoChat surpassed baselines like MiniGPT-v2 across various object sizes and tasks, demonstrating superior accuracy in bounding box prediction and significantly better region-level text captioning (achieving much higher ROUGE and METEOR scores).


