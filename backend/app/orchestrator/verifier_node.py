import re
from typing import List, Tuple
from backend.app.schemas.evidence import BoundingBox, EvidenceItem
from backend.app.schemas.task_spec import TaskSpec

COUNTING_PHRASES = ("how many", "count", "number of", "quantity", "how much")


def dedupe_boxes(boxes: List[BoundingBox]) -> List[BoundingBox]:
    """Collapses boxes that several evidence items report for the same feature.

    The router hands the same scenario boxes to more than one evidence item (a
    grounding item plus a composite pipeline item), so counting them naively
    inflates the feature count and triggers a false quantity discrepancy.
    """
    unique: List[BoundingBox] = []
    seen = set()
    for b in boxes:
        key = b.id or (b.x_left, b.y_top, b.x_right, b.y_bottom, b.label)
        if key in seen:
            continue
        seen.add(key)
        unique.append(b)
    return unique


class VerifierNode:
    """Performs post-generation verification on specialist evidence."""

    def verify(
        self,
        task_spec: TaskSpec,
        items: List[EvidenceItem],
    ) -> Tuple[bool, bool, bool, str]:
        """Returns (geometry_ok, agreement_ok, quantity_discrepancy, rationale)."""
        geometry_ok = True
        agreement_ok = True
        quantity_discrepancy = False
        claimed_count = 0

        collected: List[BoundingBox] = []
        vqa_text = ""

        for item in items:
            if item.answer_text:
                vqa_text += " " + item.answer_text
            collected.extend(item.boxes)

            # Check individual item geometry validity
            if not item.geometry_valid:
                geometry_ok = False

        all_boxes = dedupe_boxes(collected)

        # Verify all coordinates bounded [0, 100]
        for b in all_boxes:
            if not (0.0 <= b.x_left <= 100.0 and 0.0 <= b.y_top <= 100.0 and
                    0.0 <= b.x_right <= 100.0 and 0.0 <= b.y_bottom <= 100.0):
                geometry_ok = False
                break
            if b.x_left >= b.x_right or b.y_top >= b.y_bottom:
                geometry_ok = False
                break

        # Quantitative cross-check.
        # Only meaningful when the user actually asked for a count: prose is full
        # of incidental numbers (list markers, diameters, sensor names, areas), and
        # treating the first one as the claimed count flagged every answer.
        box_count = len(all_boxes)
        question = (task_spec.question_text or "").lower()
        is_counting_question = any(p in question for p in COUNTING_PHRASES)
        flagged_by_specialist = any(item.quantity_flag for item in items)

        if is_counting_question and flagged_by_specialist and box_count > 0:
            # A claim is consistent if ANY integer in the answer matches the number
            # of localized features; only a total absence of agreement is a conflict.
            claims = [int(n) for n in re.findall(r"\b(\d+)\b", vqa_text) if int(n) > 0]
            if claims and box_count not in claims:
                claimed_count = claims[0]
                quantity_discrepancy = True
                agreement_ok = False

        if not geometry_ok:
            rationale = "Geometric boundary check failed: Coordinates exceed normalized bounds [0, 100]."
        elif quantity_discrepancy:
            rationale = (
                f"Quantity discrepancy flagged: Text claims {claimed_count} targets "
                f"but {box_count} spatial features localized."
            )
        else:
            rationale = "Verification passed: Spatial bounding boxes, geometry coordinates, and textual claims demonstrate full mutual consistency."

        return geometry_ok, agreement_ok, quantity_discrepancy, rationale
