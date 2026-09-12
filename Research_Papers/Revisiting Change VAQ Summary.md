# Revisiting Change VQA in Remote Sensing with Structured and Native Multimodal Qwen Models

## Overview
This paper addresses Change Visual Question Answering (Change VQA), which involves answering natural-language questions about semantic changes between bi-temporal remote sensing (RS) image pairs[cite: 2]. It revisits the CDVQA benchmark by evaluating and comparing modern Qwen-family vision-language models (VLMs) under a unified low-rank adaptation (LoRA) setting[cite: 2].

## Main USP
The study provides a controlled comparison between two multimodal designs for temporal RS image understanding: a structured vision-language pipeline (Qwen3-VL) and a tightly integrated native multimodal model (Qwen3.5)[cite: 2]. It reveals that native multimodal designs are more effective for language-driven semantic change reasoning than explicitly structured multi-depth visual conditioning[cite: 2].

## Advantages
* Modern generalist VLMs can effectively address Change VQA without relying on handcrafted, change-specific modules[cite: 2].
* The native multimodal architecture facilitates more direct interaction between the bi-temporal images and the question, leading to better accuracy[cite: 2].
* The compact 2B parameter variant of the native model provides an optimal trade-off, delivering high accuracy without the increased inference time of larger models[cite: 2].

## Key Contributions
* The paper establishes that performance in Change VQA does not scale monotonically with model size for these VLMs[cite: 2].
* It demonstrates empirically that native multimodal models (Qwen3.5) outperform structured pipelines (Qwen3-VL) across various model scales[cite: 2].
* The Qwen3.5-2B model achieved new state-of-the-art results on the CDVQA benchmark, surpassing earlier specialized baselines like VisTA, SOBA, and the original CDVQA model[cite: 2].

## Data Set
* Models were evaluated on the CDVQA benchmark, which is derived from the SECOND semantic change detection dataset[cite: 2].
* The dataset contains 2,968 image pairs of size $512\times512$[cite: 2].
* It includes over 122,000 question-answer pairs covering various reasoning modes across six land-cover classes (e.g., water, buildings, trees)[cite: 2].

## Methodology
* The Change VQA task is framed within an autoregressive multimodal generation framework[cite: 2].
* The models process a pre-event image, a post-event image, and a question jointly[cite: 2].
* Adaptation was performed using Low-Rank Adaptation (LoRA) applied to the decoder's attention projections (query, key, value, and output), while keeping the vision encoder and visual alignment modules frozen[cite: 2].
* Training utilized a standard negative log-likelihood objective[cite: 2].

## Architecture
* **Qwen3-VL (Structured):** Utilizes a PatchMerger to map visual features into the language space, followed by "DeepStack" mergers for multi-depth visual conditioning, and relies on a full self-attention LLM decoder[cite: 2].
* **Qwen3.5 (Native):** Employs a single-stage alignment (PatchMerger) without explicit multi-depth conditioning[cite: 2]. The temporal views and questions interact directly within a hybrid multimodal decoder that combines GatedDeltaNet and full-attention layers[cite: 2].
* Both architectures utilize a shared ViT encoder (24 blocks) for initial image processing[cite: 2].

## Experimental Results
* The Qwen3.5-2B model achieved the best overall results, with an Overall Accuracy (OA) of 74.74% on test1 and 70.94% on test2[cite: 2].
* Larger models did not guarantee better results; for instance, the Qwen3-VL-8B model performed slightly worse than its 4B counterpart[cite: 2].
* Models performed well on binary directional questions (like "change or not") but struggled with fine-grained semantic comparisons (like identifying the "smallest change") and precise quantitative estimations ("change ratio")[cite: 2].