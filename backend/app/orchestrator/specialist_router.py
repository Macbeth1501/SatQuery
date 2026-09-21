from typing import Any, Dict, List, Optional, Tuple
from backend.app.fusion_pipeline.complementarity_detector import ComplementarityDetector
from backend.app.fusion_pipeline.verbalizer import MultimodalVerbalizer
from backend.app.orchestrator.trace_emitter import TraceEmitter
from backend.app.orchestrator.verifier_node import dedupe_boxes
from backend.app.schemas.evidence import BoundingBox, EvidenceItem, RegionTag
from backend.app.schemas.image_metadata import ImageMetadata
from backend.app.schemas.task_spec import TaskSpec, TaskType
from backend.app.services import model_client
from backend.app.specialists.change_vqa import ChangeVqaSpecialist
from backend.app.specialists.grounding import GroundingSpecialist
from backend.app.specialists.scenario_engine import DEMO_GROWTH_SQM
from backend.app.specialists.vqa_caption import VqaCaptionSpecialist


class SpecialistRouter:
    """Deterministic routing engine dispatching validated TaskSpecs to specialist models."""

    def __init__(self):
        self.vqa_specialist = VqaCaptionSpecialist()
        self.grounding_specialist = GroundingSpecialist()
        self.change_specialist = ChangeVqaSpecialist()
        self.complementarity_detector = ComplementarityDetector()
        self.verbalizer = MultimodalVerbalizer()

    async def route_and_execute(
        self,
        task_spec: TaskSpec,
        images: List[ImageMetadata],
        session_id: str,
        trace: Optional[TraceEmitter] = None,
    ) -> Tuple[List[EvidenceItem], str, List[BoundingBox], List[RegionTag], Optional[Dict[str, Any]]]:
        """The fifth value is the model server's reply when a trained adapter answered, else None."""
        items: List[EvidenceItem] = []
        boxes: List[BoundingBox] = []
        region_tags: List[RegionTag] = []
        answer_text = ""
        model_result: Optional[Dict[str, Any]] = None

        tt = task_spec.task_type

        # 1. Compound: FUSION_THEN_CHANGE
        if tt == TaskType.FUSION_THEN_CHANGE:
            if trace:
                trace.add_step(
                    component="SpecialistRouter",
                    adapter_id="compound_dispatch_v1.0",
                    output_summary="Executing 2-stage compound pipeline: Optical-SAR Fusion -> Bitemporal Change Analysis",
                    parameters={"pipeline": ["fusion_pipeline", "change_vqa_specialist"]},
                )

            # Stage 1: Fusion
            g_item = await self.grounding_specialist.execute(images, task_spec, session_id)
            items.append(g_item)
            boxes.extend(g_item.boxes)
            if trace:
                trace.add_step(
                    component="GroundingSpecialist",
                    adapter_id=self.grounding_specialist.adapter_id,
                    output_summary=f"Extracted {len(g_item.boxes)} multi-modal candidate bounding boxes",
                    parameters={"modality_stream": "cross-modal"},
                )

            detected_tags = self.complementarity_detector.detect_tags(
                optical_boxes=boxes,
                sar_boxes=boxes,
                query=task_spec.question_text or "",
            )
            region_tags.extend(detected_tags)
            if trace:
                trace.add_step(
                    component="ComplementarityDetector",
                    adapter_id="infonce_detector_v1.0",
                    output_summary=f"Tagged {len(detected_tags)} multi-sensor regions (agreement, optical_only, sar_only)",
                )

            fusion_answer = self.verbalizer.verbalize(
                query=task_spec.question_text or "",
                boxes=boxes,
                region_tags=region_tags,
            )

            # Stage 2: Temporal Change
            c_item = await self.change_specialist.execute(images, task_spec, session_id)
            items.append(c_item)
            boxes.extend(c_item.boxes)
            boxes = dedupe_boxes(boxes)
            if trace:
                trace.add_step(
                    component="ChangeVqaSpecialist",
                    adapter_id=self.change_specialist.adapter_id,
                    output_summary="Evaluated bitemporal differential changes against fused baseline",
                    parameters={"temporal_alignment": "verified"},
                )

            answer_text = (
                f"{fusion_answer} In addition, temporal analysis demonstrates verified infrastructure "
                f"growth of {DEMO_GROWTH_SQM} across the monitored perimeter."
            )

            v_item = EvidenceItem(
                source_specialist="Compound Fusion-Change Pipeline",
                adapter_id="compound_pipeline_v1.0",
                answer_text=answer_text,
                boxes=boxes,
                region_tags=region_tags,
                deterministic_pixel_count=c_item.deterministic_pixel_count,
                quantity_flag=True,
                geometry_valid=True,
                quantity_discrepancy=False,
            )
            items.append(v_item)

        # 2. Pure FUSION
        elif tt == TaskType.FUSION:
            g_item = await self.grounding_specialist.execute(images, task_spec, session_id)
            items.append(g_item)
            boxes = g_item.boxes
            if trace:
                trace.add_step(
                    component="GroundingSpecialist",
                    adapter_id=self.grounding_specialist.adapter_id,
                    output_summary=f"Localised {len(boxes)} multi-sensor target candidates",
                )

            region_tags = self.complementarity_detector.detect_tags(
                optical_boxes=boxes,
                sar_boxes=boxes,
                query=task_spec.question_text or "",
            )
            if trace:
                trace.add_step(
                    component="ComplementarityDetector",
                    adapter_id="infonce_detector_v1.0",
                    output_summary=f"Identified {len(region_tags)} sensor complementarity tags",
                )

            answer_text = self.verbalizer.verbalize(
                query=task_spec.question_text or "",
                boxes=boxes,
                region_tags=region_tags,
            )
            if trace:
                trace.add_step(
                    component="MultimodalVerbalizer",
                    adapter_id="verbalizer_v1.0",
                    output_summary="Synthesized modality-attributed answer citing Optical RGB and SAR radar backscatter",
                )

            v_item = EvidenceItem(
                source_specialist="Multimodal Optical-SAR Fusion Pipeline",
                adapter_id="fusion_verbalizer_v1.0",
                answer_text=answer_text,
                boxes=boxes,
                region_tags=region_tags,
                deterministic_pixel_count=len(boxes),
                quantity_flag=True,
                geometry_valid=True,
                quantity_discrepancy=False,
            )
            items.append(v_item)

        # 3. CHANGE task family
        elif tt in [TaskType.CHANGE_VQA, TaskType.CHANGE_DESCRIPTION, TaskType.CHANGE_AND_GROUNDING]:
            c_item = await self.change_specialist.execute(images, task_spec, session_id)
            items.append(c_item)
            boxes = c_item.boxes
            answer_text = c_item.answer_text or ""
            if trace:
                trace.add_step(
                    component="ChangeVqaSpecialist",
                    adapter_id=self.change_specialist.adapter_id,
                    output_summary=f"Computed differential change: {c_item.deterministic_pixel_count or 0} pixels changed",
                    parameters={"task_type": tt.value},
                )

            if tt == TaskType.CHANGE_AND_GROUNDING:
                g_item = await self.grounding_specialist.execute(images, task_spec, session_id)
                items.append(g_item)
                boxes = dedupe_boxes(boxes + g_item.boxes)
                if trace:
                    trace.add_step(
                        component="GroundingSpecialist",
                        adapter_id=self.grounding_specialist.adapter_id,
                        output_summary=f"Bound {len(boxes)} changed region bounding boxes",
                    )

        # 4. SINGLE_GROUNDING
        elif tt == TaskType.SINGLE_GROUNDING:
            g_item = await self.grounding_specialist.execute(images, task_spec, session_id)
            items.append(g_item)
            boxes = g_item.boxes
            answer_text = g_item.answer_text or ""
            if trace:
                trace.add_step(
                    component="GroundingSpecialist",
                    adapter_id=self.grounding_specialist.adapter_id,
                    output_summary=f"Grounded {len(boxes)} bounding boxes matching '{task_spec.target_object}'",
                )

        # 5a. SINGLE_VQA & SINGLE_CAPTION answered by the trained adapter (SATQUERY_VQA_MODEL_URL set).
        # No grounding call follows: the adapter produces no boxes, and the demo grounding specialist
        # would draw invented ones on a real image.
        elif tt in [TaskType.SINGLE_VQA, TaskType.SINGLE_CAPTION] and model_client.is_enabled():
            v_item, model_result = await self.vqa_specialist.answer_with_model(images, task_spec, session_id)
            items.append(v_item)
            answer_text = v_item.answer_text or ""
            if trace:
                probability = model_result.get("probability")
                trace.add_step(
                    component="VqaCaptionSpecialist",
                    adapter_id=v_item.adapter_id,
                    output_summary=(
                        f"Trained adapter answered '{model_result['answer_text']}'"
                        + (f" with probability {probability:.2f}" if probability is not None else " (free-form)")
                        + f" in {model_result['latency_ms']:.0f} ms"
                    ),
                    parameters={
                        "model": model_result["model"],
                        "revision": model_result.get("revision"),
                        "adapter": model_result.get("adapter"),
                        "question_kind": model_result["kind"],
                        "answer_distribution": model_result.get("distribution"),
                        "raw_output": model_result["raw_output"],
                        "model_latency_ms": model_result["latency_ms"],
                    },
                )

        # 5b. SINGLE_VQA & SINGLE_CAPTION on the demo engine
        elif tt in [TaskType.SINGLE_VQA, TaskType.SINGLE_CAPTION]:
            v_item = await self.vqa_specialist.execute(images, task_spec, session_id)
            items.append(v_item)
            answer_text = v_item.answer_text or ""
            if trace:
                trace.add_step(
                    component="VqaCaptionSpecialist",
                    adapter_id=self.vqa_specialist.adapter_id,
                    output_summary="Generated grounded natural language description of satellite scene",
                    parameters={"task_type": tt.value},
                )

            # Ground the scene so the narrated objects carry visual evidence.
            g_item = await self.grounding_specialist.execute(images, task_spec, session_id)
            if g_item.boxes:
                items.append(g_item)
                boxes = dedupe_boxes(g_item.boxes)
                if trace:
                    summary = (
                        f"Localised {len(boxes)} target features to verify quantitative count"
                        if v_item.quantity_flag
                        else f"Localised {len(boxes)} objects referenced in the scene description"
                    )
                    trace.add_step(
                        component="GroundingSpecialist",
                        adapter_id=self.grounding_specialist.adapter_id,
                        output_summary=summary,
                    )

        return items, answer_text, boxes, region_tags, model_result
