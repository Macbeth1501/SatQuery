import time
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from backend.app.config import APP_DESCRIPTION, APP_TITLE, APP_VERSION
from backend.app.services.storage_service import storage_service

router = APIRouter(prefix="/v1", tags=["System"])


@router.get("/health")
async def health_check():
    """Readiness check: 200 only if the session database can actually be opened.

    Container orchestration gates on this, so a service that is up but cannot store a
    session must not report healthy.
    """
    try:
        schema_version = storage_service.repository.schema_version()
    except Exception as exc:  # any failure to open the store means not ready
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "service": APP_TITLE, "error": str(exc)},
        )
    return {
        "status": "ok",
        "service": APP_TITLE,
        "version": APP_VERSION,
        "description": APP_DESCRIPTION,
        "database": {"schemaVersion": schema_version},
        "timestamp": int(time.time()),
    }


@router.get("/registry")
async def get_registry():
    """Returns registered specialist models, adapters, and precondition rules."""
    return {
        "specialists": [
            {
                "id": "vqa_caption_adapter_v1.0",
                "name": "VQA / Remote-Sensing Captioning Specialist",
                "supported_tasks": ["single_vqa", "single_caption"],
                "input_modalities": ["optical", "multispectral"],
                "status": "ready",
            },
            {
                "id": "grounding_adapter_v1.0",
                "name": "Visual Grounding Specialist",
                "supported_tasks": ["single_grounding", "change_and_grounding"],
                "input_modalities": ["optical", "multispectral", "sar"],
                "status": "ready",
            },
            {
                "id": "change_vqa_adapter_v1.0",
                "name": "Bitemporal Change VQA Specialist",
                "supported_tasks": ["change_vqa", "change_description", "fusion_then_change"],
                "input_modalities": ["optical", "multispectral"],
                "status": "ready",
            },
            {
                "id": "fusion_verbalizer_v1.0",
                "name": "Multimodal Optical-SAR Fusion Pipeline",
                "supported_tasks": ["fusion", "fusion_then_change"],
                "input_modalities": ["optical", "sar"],
                "status": "ready",
            },
        ],
        "preconditions": [
            {
                "code": "unsupported_format",
                "name": "Raster Format Validator",
                "description": "Enforces GeoTIFF, TIFF, PNG, or JPEG raster decoding standards.",
            },
            {
                "code": "insufficient_image_count",
                "name": "Input Count Checker",
                "description": "Verifies that multi-temporal or multimodal tasks have the required raster inputs.",
            },
            {
                "code": "modality_mismatch",
                "name": "Radiometric Modality Checker",
                "description": "Enforces physical sensor pairing rules (prevents Optical-SAR differential change).",
            },
            {
                "code": "crs_mismatch_unresolvable",
                "name": "Spatial Reference Validator",
                "description": "Confirms coordinate reference system transformability.",
            },
            {
                "code": "insufficient_footprint_overlap",
                "name": "Geographic Intersection Checker",
                "description": "Ensures bitemporal imagery shares >= 70% spatial footprint overlap.",
            },
            {
                "code": "temporal_ordering_invalid",
                "name": "Chronological Alignment Checker",
                "description": "Validates that T1 acquisition precedes T2 acquisition.",
            },
            {
                "code": "ambiguous_intent",
                "name": "Query Intent Resolver",
                "description": "Screens ambiguous or unresolvable natural language prompts.",
            },
            {
                "code": "no_trained_model",
                "name": "Trained Model Gate",
                "description": (
                    "With the live model on, refuses grounding, change and fusion on non-demo images, "
                    "since only single-image yes/no and a-d questions have a trained model."
                ),
            },
        ],
    }
