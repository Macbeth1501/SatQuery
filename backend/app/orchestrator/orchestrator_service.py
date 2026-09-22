import uuid
from typing import Any, Dict, List, Optional
from backend.app.orchestrator.compatibility_validator import CompatibilityValidator
from backend.app.orchestrator.confidence_scorer import ConfidenceScorer
from backend.app.orchestrator.query_interpreter import QueryInterpreter
from backend.app.orchestrator.response_composer import response_composer
from backend.app.orchestrator.specialist_router import SpecialistRouter
from backend.app.orchestrator.trace_emitter import TraceEmitter
from backend.app.orchestrator.verifier_node import VerifierNode
from backend.app.schemas.api_models import AnalyzeResponse
from backend.app.schemas.image_metadata import ImageMetadata
from backend.app.schemas.validation import ValidationPass, ValidationRejection
from backend.app.services.overlay_service import overlay_service
from backend.app.services.storage_service import storage_service


class OrchestratorService:
    """Master orchestrator executing the GeoGraphRAG & Verifier-in-the-Loop workflow."""

    def __init__(self):
        self.query_interpreter = QueryInterpreter()
        self.compatibility_validator = CompatibilityValidator()
        self.specialist_router = SpecialistRouter()
        self.verifier_node = VerifierNode()
        self.confidence_scorer = ConfidenceScorer()
        self.response_composer = response_composer

    async def run_pipeline(
        self,
        query: str,
        images: List[ImageMetadata],
        session_id: Optional[str] = None,
        session_options: Optional[Dict[str, Any]] = None,
    ) -> AnalyzeResponse:
        session_id = session_id or f"sq-{uuid.uuid4().hex[:8]}"
        session_dir = storage_service.get_session_dir(session_id)
        trace = TraceEmitter(session_id=session_id)

        # Step 1: Query Interpretation
        trace.add_step(
            component="QueryInterpreter",
            adapter_id="intent_classifier_v1.0",
            output_summary=f"Parsed natural language query: '{query}'",
            parameters={"query": query},
        )
        task_spec = self.query_interpreter.interpret(query, images)

        # Step 2: Compatibility Validation (Preconditions)
        trace.add_step(
            component="CompatibilityValidator",
            adapter_id="geographrag_preconditions_v1.0",
            output_summary=f"Evaluated physical preconditions for task '{task_spec.task_type.value}'",
            parameters={
                "required_image_count": task_spec.required_image_count,
                "input_images": [img.name for img in images],
            },
        )
        validation_result = self.compatibility_validator.validate(task_spec, images)

        # Handle Rejection gracefully
        if isinstance(validation_result, ValidationRejection):
            trace.add_step(
                component="PreconditionGate",
                adapter_id="rejection_handler_v1.0",
                output_summary=f"Analysis terminated: {validation_result.reason_code.value} - {validation_result.human_readable_reason}",
                status="rejected",
            )
            execution_trace = trace.build_trace(
                selected_task_type=task_spec.task_type.value,
                confidence_tier="Low",
                confidence_rationale="Execution halted by physical precondition validator.",
                rejection=validation_result,
            )

            response = self.response_composer.compose_rejection_response(
                session_id=session_id,
                rejection=validation_result,
                execution_trace=execution_trace,
                task_spec=task_spec,
            )
            storage_service.store_session_response(session_id, response, query=query)
            return response

        # Step 3: Specialist Routing & Execution
        items, answer_text, boxes, region_tags, model_result, demo_confidence = await self.specialist_router.route_and_execute(
            task_spec, images, session_id, trace=trace
        )

        # Step 4: Verifier Node
        trace.add_step(
            component="VerifierNode",
            adapter_id="spatial_consistency_verifier_v1.0",
            output_summary=f"Audited {len(boxes)} spatial features, geometry constraints, and cross-tool consistency",
        )
        geometry_ok, agreement_ok, qty_discrepancy, verifier_rationale = self.verifier_node.verify(
            task_spec, items
        )

        # Step 5: Visual Evidence Overlay Rendering
        has_change = "change" in task_spec.task_type.value
        overlay_urls, generated_masks = overlay_service.generate_visual_overlays(
            session_id=session_id,
            session_dir=session_dir,
            boxes=boxes,
            has_change_mask=has_change,
        )
        trace.add_step(
            component="VisualOverlayRenderer",
            adapter_id="evidence_rasterizer_v1.0",
            output_summary=f"Rendered {len(overlay_urls)} visual bounding box overlay(s) and {len(generated_masks)} mask layer(s)",
        )

        # Step 6: Confidence Scoring
        trace.add_step(
            component="ConfidenceScorer",
            adapter_id="bayesian_confidence_scorer_v1.0",
            output_summary=(
                "Calculated confidence tier from the trained adapter's answer probability"
                if model_result is not None
                else "Calculated confidence tier based on verifier flags, sensor parameters, and scenario calibration"
            ),
        )
        confidence = self.confidence_scorer.compute(
            task_spec=task_spec,
            images=images,
            geometry_ok=geometry_ok,
            agreement_ok=agreement_ok,
            quantity_discrepancy=qty_discrepancy,
            verifier_rationale=verifier_rationale,
            model_result=model_result,
            demo_confidence=demo_confidence,
        )

        # Step 7: Response Assembly
        trace.add_step(
            component="ResponseComposer",
            output_summary="Assembled final grounded JSON payload with full audit trace",
        )
        execution_trace = trace.build_trace(
            selected_task_type=task_spec.task_type.value,
            confidence_tier=confidence.tier,
            confidence_rationale=confidence.rationale,
            rejection=None,
        )

        response = self.response_composer.compose_success_response(
            session_id=session_id,
            answer_text=answer_text,
            boxes=boxes,
            masks=generated_masks,
            region_tags=region_tags,
            overlay_image_urls=overlay_urls,
            confidence=confidence,
            execution_trace=execution_trace,
            task_spec=task_spec,
        )

        storage_service.store_session_response(session_id, response, query=query)
        return response


orchestrator_service = OrchestratorService()
