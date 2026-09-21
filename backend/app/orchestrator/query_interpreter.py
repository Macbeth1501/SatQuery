import re
from typing import List, Optional
from backend.app.schemas.image_metadata import ImageMetadata
from backend.app.schemas.task_spec import TaskSpec, TaskType


# "a) ... b) ..." -- at least two lettered options.
CHOICE_OPTIONS = re.compile(r"(?:^|[\s,;:?])a\)\s.*(?:^|[\s,;])b\)\s")


class QueryInterpreter:
    """Classifies natural language query into a formal TaskSpec covering all 8 task types."""

    def interpret(self, query: str, images: List[ImageMetadata]) -> TaskSpec:
        q = query.strip()
        q_lower = q.lower()
        image_count = len(images)

        # 0. Check for ambiguous / underspecified intent
        if len(q) < 4 or q_lower in ["hello", "hi", "test", "what", "where", "image", "satellite", "analyze"]:
            return TaskSpec(
                task_type=TaskType.SINGLE_VQA,
                status="ambiguous",
                target_object=None,
                question_text=q,
                required_image_count=1,
                required_modalities=["optical"],
                requires_temporal_pairing=False,
                intent_confidence=0.35,
                clarifying_question=(
                    "Query is underspecified. Please specify targets and intent "
                    "(e.g., 'Locate all fuel storage tanks' or 'Identify naval vessels under cloud cover')."
                ),
            )

        # Detect modalities present in input images
        modalities = [
            img.detected_modality.value if hasattr(img.detected_modality, "value") else str(img.detected_modality)
            for img in images
        ]
        has_sar = "sar" in modalities or any(m in ["sar", "radar"] for m in modalities)
        has_optical = any(m in ["optical", "multispectral"] for m in modalities)
        is_multimodal_input = has_sar and has_optical and image_count >= 2

        # Keywords for intent detection
        # "between" is deliberately absent: on its own it reads "adjacency between X and Y" or
        # "an area between 0 and 576000 sqm" as a change request. Every real change query in the
        # demos and tests also carries "change", "difference" or a similar cue.
        change_keywords = [
            "change", "difference", "expansion", "growth",
            "demolition", "new construction", "before and after", "t1", "t2",
            "increased", "decreased", "years", "temporal"
        ]
        fusion_keywords = [
            "fusion", "optical and sar", "sar and optical", "radar",
            "cloud cover", "penetrat", "cross-modal", "multimodal", "synthetic aperture"
        ]
        grounding_keywords = [
            "locate", "ground", "box", "boxes", "bounding box",
            "where are", "where is", "coordinates", "highlight", "show me all", "pinpoint"
        ]
        caption_keywords = [
            "describe", "caption", "scene summary", "overview", "summarize", "scene description"
        ]

        # A question that lists a) b) ... options asks for one of them: it is answered, never
        # grounded or captioned, even when it says "where is" (e.g. "where is the forest? a) to the left ...").
        is_choice_question = bool(CHOICE_OPTIONS.search(q_lower))

        query_has_change = any(k in q_lower for k in change_keywords)
        query_has_fusion = any(k in q_lower for k in fusion_keywords)
        is_grounding_query = any(k in q_lower for k in grounding_keywords) and not is_choice_question
        is_caption_query = any(k in q_lower for k in caption_keywords) and not is_choice_question

        # 1. Compound: fusion_then_change
        # Specifically when query contains both fusion terms AND change terms
        if query_has_fusion and query_has_change:
            return TaskSpec(
                task_type=TaskType.FUSION_THEN_CHANGE,
                status="resolved",
                target_object=self._extract_target(q_lower),
                question_text=q,
                required_image_count=2,
                required_modalities=["optical", "sar"],
                requires_temporal_pairing=True,
                intent_confidence=0.96,
            )

        # 2. Change task family
        # If query asks for change, difference, or comparison
        # Two same-sensor images do not by themselves mean the user wants change analysis;
        # ask rather than guess.
        if image_count >= 2 and not query_has_change and not query_has_fusion and not is_multimodal_input:
            return TaskSpec(
                task_type=TaskType.SINGLE_VQA,
                status="ambiguous",
                target_object=self._extract_target(q_lower),
                question_text=q,
                required_image_count=2,
                required_modalities=["optical", "optical"],
                requires_temporal_pairing=False,
                intent_confidence=0.45,
                clarifying_question=(
                    "You supplied two images but the query does not say how to use them. "
                    "Ask what changed between them (e.g., 'What changed between these two dates?'), "
                    "or upload a single image for a one-image question."
                ),
            )

        if query_has_change:
            if is_grounding_query:
                task_type = TaskType.CHANGE_AND_GROUNDING
            elif is_caption_query:
                task_type = TaskType.CHANGE_DESCRIPTION
            else:
                task_type = TaskType.CHANGE_VQA

            return TaskSpec(
                task_type=task_type,
                status="resolved",
                target_object=self._extract_target(q_lower),
                question_text=q,
                required_image_count=2,
                required_modalities=["optical", "optical"],
                requires_temporal_pairing=True,
                intent_confidence=0.94,
            )

        # 3. Pure Fusion
        # If query has fusion keywords, or multimodal images uploaded without change intent
        if query_has_fusion or is_multimodal_input:
            return TaskSpec(
                task_type=TaskType.FUSION,
                status="resolved",
                target_object=self._extract_target(q_lower),
                question_text=q,
                required_image_count=2,
                required_modalities=["optical", "sar"],
                requires_temporal_pairing=False,
                intent_confidence=0.95,
            )

        # 4. Single Grounding
        if is_grounding_query:
            return TaskSpec(
                task_type=TaskType.SINGLE_GROUNDING,
                status="resolved",
                target_object=self._extract_target(q_lower),
                question_text=q,
                required_image_count=1,
                required_modalities=["optical"],
                requires_temporal_pairing=False,
                intent_confidence=0.95,
            )

        # 5. Single Caption
        if is_caption_query:
            return TaskSpec(
                task_type=TaskType.SINGLE_CAPTION,
                status="resolved",
                target_object=None,
                question_text=q,
                required_image_count=1,
                required_modalities=["optical"],
                requires_temporal_pairing=False,
                intent_confidence=0.92,
            )

        # 6. Default: Single VQA
        return TaskSpec(
            task_type=TaskType.SINGLE_VQA,
            status="resolved",
            target_object=self._extract_target(q_lower),
            question_text=q,
            required_image_count=1,
            required_modalities=["optical"],
            requires_temporal_pairing=False,
            intent_confidence=0.90,
        )

    def _extract_target(self, q_lower: str) -> Optional[str]:
        if "tank" in q_lower:
            return "fuel storage tanks"
        if "vessel" in q_lower or "ship" in q_lower or "boat" in q_lower:
            return "maritime vessels"
        if "aircraft" in q_lower or "plane" in q_lower or "runway" in q_lower or "airport" in q_lower:
            return "aircraft / runway"
        if "water" in q_lower or "river" in q_lower or "lake" in q_lower:
            return "water body / hydrology"
        if "road" in q_lower or "bridge" in q_lower or "highway" in q_lower:
            return "transportation network"
        if "building" in q_lower or "structure" in q_lower or "construction" in q_lower:
            return "buildings / infrastructure"
        return "infrastructure features"
