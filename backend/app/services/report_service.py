import io
from html import escape
from pathlib import Path
from typing import Optional

from backend.app import config
from backend.app.schemas.api_models import AnalyzeResponse

BADGE_CLASSES = {"High": "badge-high", "Medium": "badge-med", "Low": "badge-low"}


def _resolve_storage_uri(uri: str) -> Optional[Path]:
    """Maps a served /storage/... URI back to the file on disk.

    The PDF renderer has no HTTP client, so evidence images referenced by URL have
    to be resolved locally. Anything outside the storage root is refused.
    """
    marker = "/storage/"
    idx = uri.find(marker)
    if idx == -1:
        return None
    relative = uri[idx + len(marker):].split("?", 1)[0].lstrip("/")
    storage_root = Path(config.STORAGE_DIR).resolve()
    candidate = (storage_root / relative).resolve()
    try:
        candidate.relative_to(storage_root)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


class ReportService:
    """Renders downloadable reports (PDF and JSON) with full content parity."""

    def render_json(self, response: AnalyzeResponse) -> str:
        return response.model_dump_json(by_alias=True, indent=2)

    def render_html_report(self, response: AnalyzeResponse) -> str:
        """Generates clean, printable HTML report with complete content parity."""
        trace_rows = "".join([
            f"""<tr>
                <td style="padding: 6px 10px; border: 1px solid #ddd;">{s.step_index}</td>
                <td style="padding: 6px 10px; border: 1px solid #ddd;"><strong>{escape(s.component)}</strong></td>
                <td style="padding: 6px 10px; border: 1px solid #ddd;">{escape(s.adapter_id_or_version or 'N/A')}</td>
                <td style="padding: 6px 10px; border: 1px solid #ddd;">{s.wall_clock_ms} ms</td>
                <td style="padding: 6px 10px; border: 1px solid #ddd;">{escape(s.output_summary)}</td>
            </tr>"""
            for s in response.execution_trace.steps
        ])

        tier = response.confidence.tier
        badge_class = BADGE_CLASSES.get(tier, "badge-med")
        boxes_count = len(response.evidence.boxes)

        # Evidence imagery: the on-screen Results page shows the annotated overlay,
        # so the report has to carry it too for content parity.
        image_uris = list(response.evidence.overlay_image_urls) + list(response.evidence.masks)
        evidence_images = "".join(
            f'''<div style="margin-top: 12px;">
                <img src="{uri}" style="max-width: 420px; border: 1px solid #cbd5e1;" />
                <p style="font-size: 10px; color: #94a3b8; margin: 4px 0 0;">{escape(uri.rsplit("/", 1)[-1])}</p>
            </div>'''
            for uri in image_uris
        )

        boxes_table = ""
        if response.evidence.boxes:
            rows = "".join(
                f'''<tr>
                    <td style="padding: 4px 8px; border: 1px solid #ddd;">{escape(b.label or b.id or "-")}</td>
                    <td style="padding: 4px 8px; border: 1px solid #ddd;">{b.x_left:.1f}, {b.y_top:.1f} &rarr; {b.x_right:.1f}, {b.y_bottom:.1f}</td>
                    <td style="padding: 4px 8px; border: 1px solid #ddd;">{f"{b.score:.2f}" if b.score is not None else "-"}</td>
                </tr>'''
                for b in response.evidence.boxes
            )
            boxes_table = f'''<table style="margin-top: 12px;">
                <thead><tr><th>Feature</th><th>Bounds (0-100)</th><th>Score</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>'''
        tags_count = len(response.evidence.region_tags or [])

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>SatQuery AI Analysis Report - {escape(response.session_id)}</title>
    <style>
        body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #1e293b; line-height: 1.5; padding: 30px; }}
        h1, h2, h3 {{ color: #0f172a; margin-top: 0; }}
        .badge {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; }}
        .badge-high {{ background: #dcfce7; color: #15803d; }}
        .badge-med {{ background: #fef3c7; color: #b45309; }}
        .badge-low {{ background: #ffe4e6; color: #be123c; }}
        .card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
        th {{ background: #f1f5f9; text-align: left; padding: 8px 10px; border: 1px solid #cbd5e1; }}
    </style>
</head>
<body>
    <div style="border-bottom: 2px solid #0284c7; padding-bottom: 12px; margin-bottom: 20px;">
        <h2>SatQuery AI — Remote Sensing Analysis Report</h2>
        <p style="color: #64748b; font-size: 12px; margin: 0;">
            SIH26167 • Indian Space Research Organisation (ISRO) | Session ID: <strong>{escape(response.session_id)}</strong>
        </p>
    </div>

    <div class="card">
        <h3>1. Executive Grounded Answer</h3>
        <p style="font-size: 14px; line-height: 1.6;">{escape(response.answer_text or 'Analysis terminated with physical rejection.')}</p>
        <div>
            <strong>Confidence Tier:</strong> 
            <span class="badge {badge_class}">{escape(tier)} CONFIDENCE</span>
            <p style="font-size: 12px; color: #475569; margin: 6px 0 0;">Rationale: {escape(response.confidence.rationale)}</p>
        </div>
    </div>

    <div class="card">
        <h3>2. Evidence Summary</h3>
        <p style="font-size: 12px; color: #475569;">
            Detected Features: <strong>{boxes_count} Bounding Boxes</strong> | 
            Complementarity Tags: <strong>{tags_count} Multi-Sensor Regions</strong>
        </p>
        {evidence_images}
        {boxes_table}
    </div>

    <div class="card">
        <h3>3. Auditable Execution Trace</h3>
        <table>
            <thead>
                <tr>
                    <th>Step</th>
                    <th>Component</th>
                    <th>Adapter</th>
                    <th>Duration</th>
                    <th>Output Summary</th>
                </tr>
            </thead>
            <tbody>
                {trace_rows}
            </tbody>
        </table>
    </div>

    <div style="font-size: 11px; color: #94a3b8; text-align: center; margin-top: 30px;">
        Generated by SatQuery AI Engine • GeoGraphRAG Precondition Enforced • Verifier-in-the-Loop
    </div>
</body>
</html>"""
        return html

    def render_pdf(self, response: AnalyzeResponse) -> bytes:
        """Renders the same report as a real PDF.

        xhtml2pdf is pure Python, so a demo machine needs no native GTK/Qt
        libraries the way WeasyPrint or wkhtmltopdf would.
        """
        from xhtml2pdf import pisa

        def link_callback(uri: str, _rel: str) -> str:
            resolved = _resolve_storage_uri(uri)
            return str(resolved) if resolved else uri

        html = self.render_html_report(response)
        buffer = io.BytesIO()
        result = pisa.CreatePDF(html, dest=buffer, link_callback=link_callback)
        if result.err:
            raise RuntimeError(f"PDF rendering failed with {result.err} error(s).")
        return buffer.getvalue()

    def get_or_render_pdf(self, response: AnalyzeResponse, session_dir: Path) -> bytes:
        """Returns the cached PDF for a session, rendering it once on first request.

        Session ids are unique per analysis, so a cached file can never be stale.
        """
        pdf_path = session_dir / "report.pdf"
        if pdf_path.is_file():
            return pdf_path.read_bytes()
        pdf_bytes = self.render_pdf(response)
        pdf_path.write_bytes(pdf_bytes)
        return pdf_bytes


report_service = ReportService()
