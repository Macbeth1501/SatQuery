"""Unit tests for the precondition validator (no server, no HTTP)."""
import pytest

from backend.app.orchestrator.compatibility_validator import CompatibilityValidator
from backend.app.schemas.image_metadata import ImageMetadata
from backend.app.schemas.task_spec import TaskSpec, TaskStatus, TaskType
from backend.app.schemas.validation import (
    RejectionReasonCode,
    ValidationPass,
    ValidationRejection,
)


@pytest.fixture
def validator():
    return CompatibilityValidator()


def image(name="scene.tif", fmt="geotiff", modality="optical", **kwargs):
    return ImageMetadata(image_id=name, name=name, format=fmt, detected_modality=modality, **kwargs)


def change_spec():
    return TaskSpec(
        task_type=TaskType.CHANGE_VQA,
        question_text="what changed between these two dates?",
        required_image_count=2,
        requires_temporal_pairing=True,
    )


def test_unsupported_format_is_rejected(validator):
    spec = TaskSpec(task_type=TaskType.SINGLE_VQA, question_text="count the tanks")
    result = validator.validate(spec, [image(name="scene.bmp", fmt="bmp")])
    assert isinstance(result, ValidationRejection)
    assert result.reason_code == RejectionReasonCode.UNSUPPORTED_FORMAT


def test_insufficient_image_count_is_rejected(validator):
    result = validator.validate(change_spec(), [image()])
    assert isinstance(result, ValidationRejection)
    assert result.reason_code == RejectionReasonCode.INSUFFICIENT_IMAGE_COUNT


def test_optical_sar_pair_rejected_for_change_detection(validator):
    """The signature rule: mismatched sensor physics cannot yield physical change."""
    images = [image(name="optical.tif"), image(name="sar.tif", modality="sar")]
    result = validator.validate(change_spec(), images)
    assert isinstance(result, ValidationRejection)
    assert result.reason_code == RejectionReasonCode.MODALITY_MISMATCH
    assert "fusion" in result.suggested_action.lower()


def test_temporal_ordering_is_enforced(validator):
    images = [
        image(name="t1.tif", acquisition_timestamp="2024-06-01T00:00:00Z"),
        image(name="t2.tif", acquisition_timestamp="2023-01-01T00:00:00Z"),
    ]
    result = validator.validate(change_spec(), images)
    assert isinstance(result, ValidationRejection)
    assert result.reason_code == RejectionReasonCode.TEMPORAL_ORDERING_INVALID


def test_insufficient_footprint_overlap_is_rejected(validator):
    images = [image(name="a.tif", footprint_overlap_percent=12.0), image(name="b.tif")]
    result = validator.validate(change_spec(), images)
    assert isinstance(result, ValidationRejection)
    assert result.reason_code == RejectionReasonCode.INSUFFICIENT_FOOTPRINT_OVERLAP


def test_unresolvable_crs_is_rejected(validator):
    images = [
        image(name="a.tif", crs="LOCAL_UNRESOLVABLE_GRID"),
        image(name="b.tif", crs="EPSG:4326"),
    ]
    result = validator.validate(change_spec(), images)
    assert isinstance(result, ValidationRejection)
    assert result.reason_code == RejectionReasonCode.CRS_MISMATCH_UNRESOLVABLE


def test_ambiguous_intent_is_rejected(validator):
    spec = TaskSpec(task_type=TaskType.SINGLE_VQA, status=TaskStatus.AMBIGUOUS, question_text="hi")
    result = validator.validate(spec, [image()])
    assert isinstance(result, ValidationRejection)
    assert result.reason_code == RejectionReasonCode.AMBIGUOUS_INTENT


def test_valid_pair_passes(validator):
    images = [
        image(name="t1.tif", acquisition_timestamp="2023-01-01T00:00:00Z"),
        image(name="t2.tif", acquisition_timestamp="2024-06-01T00:00:00Z"),
    ]
    result = validator.validate(change_spec(), images)
    assert isinstance(result, ValidationPass)
    assert result.warnings == []
