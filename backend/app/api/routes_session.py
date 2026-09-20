from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import HTMLResponse
from backend.app.schemas.api_models import AnalyzeResponse
from backend.app.services.report_service import report_service
from backend.app.services.storage_service import storage_service

router = APIRouter(prefix="/v1", tags=["Session & Reports"])


@router.get("/session/{session_id}", response_model=AnalyzeResponse)
async def get_session(session_id: str) -> AnalyzeResponse:
    """Retrieves full analysis response and execution trace for a given session."""
    response = storage_service.get_session_response(session_id)
    if not response:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return response


@router.get("/session/{session_id}/report")
async def get_session_report(
    session_id: str,
    format: str = Query(default="pdf", pattern="^(pdf|json|html)$"),
):
    """Generates downloadable analysis report with complete data parity."""
    response = storage_service.get_session_response(session_id)
    if not response:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")

    if response.rejected:
        # A rejected analysis produced no evidence, so there is nothing to report.
        raise HTTPException(
            status_code=409,
            detail=(
                f"Session '{session_id}' was rejected at the compatibility check, "
                "so no analysis report exists. Retrieve the session itself to read "
                "the rejection reason and its execution trace."
            ),
        )

    if format == "json":
        return Response(
            content=report_service.render_json(response),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=satquery_report_{session_id}.json"},
        )

    if format == "html":
        return HTMLResponse(content=report_service.render_html_report(response))

    session_dir = storage_service.get_session_dir(session_id)
    try:
        pdf_bytes = report_service.get_or_render_pdf(response, session_dir)
    except Exception as exc:  # renderer failure must not lose the report entirely
        raise HTTPException(
            status_code=500, detail=f"Report rendering failed: {exc}"
        ) from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="satquery_report_{session_id}.pdf"'
            )
        },
    )
