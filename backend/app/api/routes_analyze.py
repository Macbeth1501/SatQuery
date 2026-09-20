import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from backend.app.orchestrator.orchestrator_service import orchestrator_service
from backend.app.schemas.api_models import AnalyzeResponse
from backend.app.services.metadata_service import metadata_service
from backend.app.services.storage_service import storage_service

router = APIRouter(prefix="/v1", tags=["Analysis"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    query: str = Form(...),
    files: Optional[List[UploadFile]] = File(default=None),
    session_options: Optional[str] = Form(default=None),
) -> AnalyzeResponse:
    """Analyzes 1 or 2 satellite rasters with natural language query."""
    uploaded_files = files or []
    if len(uploaded_files) > 2:
        raise HTTPException(
            status_code=400,
            detail="SatQuery AI accepts a maximum of 2 images per session.",
        )

    session_id = f"sq-{uuid.uuid4().hex[:8]}"
    saved_files = await storage_service.save_uploaded_files(session_id, uploaded_files)

    # Extract metadata for each raster
    images_metadata = []
    for idx, f_info in enumerate(saved_files):
        meta = metadata_service.inspect_file(
            file_path=f_info["path"],
            filename=f_info["filename"],
            index=idx + 1,
        )
        meta.preview_url = f"/storage/sessions/{session_id}/inputs/{f_info['stored_name']}"
        images_metadata.append(meta)

    # Pair-level facts (footprint overlap) can only be known once both images are read.
    metadata_service.annotate_pair(images_metadata)

    # Parse session options if provided
    options_dict = None
    if session_options:
        try:
            options_dict = json.loads(session_options)
        except Exception:
            pass

    response = await orchestrator_service.run_pipeline(
        query=query,
        images=images_metadata,
        session_id=session_id,
        session_options=options_dict,
    )

    return response
