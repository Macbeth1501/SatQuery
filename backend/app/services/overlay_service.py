import os
from pathlib import Path
from typing import List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
from backend.app.schemas.evidence import BoundingBox


class OverlayService:
    """Generates visual bounding-box overlays and translucent change masks on remote sensing imagery."""

    def generate_visual_overlays(
        self,
        session_id: str,
        session_dir: Path,
        boxes: List[BoundingBox],
        has_change_mask: bool = False,
    ) -> Tuple[List[str], List[str]]:
        evidence_dir = session_dir / "evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)

        inputs_dir = session_dir / "inputs"
        input_files = list(inputs_dir.glob("*")) if inputs_dir.exists() else []

        # Try opening base image or construct a realistic raster canvas
        base_img = None
        if input_files:
            try:
                base_img = Image.open(input_files[0]).convert("RGBA")
            except Exception:
                base_img = None

        if base_img is None or base_img.width < 10 or base_img.height < 10:
            # Create a 640x640 synthetic remote sensing canvas (dark ocean/port tones)
            base_img = Image.new("RGBA", (640, 640), color=(15, 23, 42, 255))
            draw_bg = ImageDraw.Draw(base_img)
            # Draw synthetic port / coastline geometry
            draw_bg.polygon([(0, 180), (320, 240), (640, 200), (640, 640), (0, 640)], fill=(30, 41, 59, 255))
            draw_bg.rectangle([(160, 280), (480, 520)], fill=(51, 65, 85, 255), outline=(71, 85, 105, 255))

        w, h = base_img.size

        # 1. Generate Annotated Bounding Box Overlay
        overlay_img = base_img.copy()
        draw = ImageDraw.Draw(overlay_img)

        box_colors = [
            (6, 182, 212, 255),   # Cyan
            (16, 185, 129, 255),  # Emerald
            (245, 158, 11, 255),  # Amber
            (168, 85, 247, 255),  # Purple
        ]

        for idx, box in enumerate(boxes):
            x1 = int(box.x_left * w / 100.0)
            y1 = int(box.y_top * h / 100.0)
            x2 = int(box.x_right * w / 100.0)
            y2 = int(box.y_bottom * h / 100.0)
            color = box_colors[idx % len(box_colors)]

            # Draw outer rectangle
            draw.rectangle([(x1, y1), (x2, y2)], outline=color, width=3)

            # Draw label tag banner
            label = box.label or f"Target {idx + 1}"
            score_text = f" ({box.score:.2f})" if box.score else ""
            full_label = f"{label}{score_text}"

            tag_y1 = max(0, y1 - 20)
            tag_y2 = y1
            tag_x2 = min(w, x1 + len(full_label) * 8 + 12)
            draw.rectangle([(x1, tag_y1), (tag_x2, tag_y2)], fill=color)
            draw.text((x1 + 4, tag_y1 + 3), full_label, fill=(15, 23, 42, 255))

        overlay_filename = "evidence_boxes_overlay.png"
        overlay_path = evidence_dir / overlay_filename
        overlay_img.save(overlay_path, format="PNG")

        overlay_urls = [f"/storage/sessions/{session_id}/evidence/{overlay_filename}"]

        # 2. Generate Change Mask if requested
        masks = []
        if has_change_mask:
            mask_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            mask_draw = ImageDraw.Draw(mask_img)

            # Draw semi-transparent red/amber highlighted change polygon
            for box in boxes:
                bx1 = int(box.x_left * w / 100.0)
                by1 = int(box.y_top * h / 100.0)
                bx2 = int(box.x_right * w / 100.0)
                by2 = int(box.y_bottom * h / 100.0)
                mask_draw.rectangle([(bx1, by1), (bx2, by2)], fill=(239, 68, 68, 120), outline=(239, 68, 68, 220), width=2)

            mask_filename = "mask_layer_01.png"
            mask_path = evidence_dir / mask_filename
            mask_img.save(mask_path, format="PNG")
            masks.append(f"/storage/sessions/{session_id}/evidence/{mask_filename}")

        return overlay_urls, masks


overlay_service = OverlayService()
