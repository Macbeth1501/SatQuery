"""Regenerate the demo GeoTIFFs served from frontend/public/demo/.

The pictures are synthetic: a Pillow port of the SVG scenes in
frontend/src/data/mockImagery.ts, drawn to fit the bounding boxes the backend returns for each
demo (frontend/src/data/demoParity.json). What is real is the georeferencing -- CRS, geotransform,
ground sample distance, platform and acquisition tags -- which rasterio and MetadataService read
back exactly as they would from a real scene. Every file carries a DEMO_NOTE tag saying so.

    python tools/make_demo_rasters.py

Scenarios B and F stay plain PNGs on purpose: they exercise the "no georeference" path, where the
metadata service must report unknowns rather than invent values.
"""
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import rasterio
from PIL import Image, ImageDraw, ImageFont
from rasterio.transform import from_origin
from rasterio.warp import transform as warp_transform

OUT_DIR = Path(__file__).resolve().parents[1] / "frontend" / "public" / "demo"

W, H = 600, 400  # logical canvas, matching mockImagery.ts
SS = 2  # supersampling factor for anti-aliasing

DEMO_NOTE = (
    "Synthetic demonstration scene. The georeferencing is valid but the picture was drawn, "
    "not acquired by the named platform."
)

WATER_A, WATER_B = (0x0F, 0x38, 0x54), (0x1E, 0x5C, 0x82)
CONTAINER_COLORS = ["#b5482f", "#2f5f8f", "#c9a227", "#4f7a4a", "#8a8a8a", "#a33b3b"]

Color = str


def _rgb(color: Color) -> Tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def X(pct: float) -> float:
    return pct * W / 100


def Y(pct: float) -> float:
    return pct * H / 100


class Canvas:
    """Draws in the 600x400 logical space of the SVG scenes onto a supersampled RGB image."""

    def __init__(self) -> None:
        self.img = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 255))
        self._gradient: Optional[Image.Image] = None

    # -- primitives -----------------------------------------------------------------------

    def _scaled(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        return [(x * SS, y * SS) for x, y in points]

    def _fill(self, mask_draw, fill: Color, opacity: float) -> None:
        """Composite a filled shape. `mask_draw(draw, fill_value)` paints into an L mask."""
        mask = Image.new("L", self.img.size, 0)
        mask_draw(ImageDraw.Draw(mask), int(255 * opacity))
        if fill == "url(#water)":
            layer = self._water()
        else:
            layer = Image.new("RGBA", self.img.size, _rgb(fill) + (255,))
        self.img.paste(layer, (0, 0), mask)

    def _water(self) -> Image.Image:
        if self._gradient is None:
            w, h = self.img.size
            t = (np.linspace(0, 1, w)[None, :] + np.linspace(0, 1, h)[:, None]) / 2.0
            arr = np.zeros((h, w, 4), dtype=np.uint8)
            for i in range(3):
                arr[..., i] = (WATER_A[i] + (WATER_B[i] - WATER_A[i]) * t).astype(np.uint8)
            arr[..., 3] = 255
            self._gradient = Image.fromarray(arr, "RGBA")
        return self._gradient

    def rect(self, x, y, w, h, fill: Color, opacity: float = 1.0) -> None:
        pts = self._scaled([(x, y), (x + w, y + h)])
        self._fill(lambda d, v: d.rectangle([pts[0], pts[1]], fill=v), fill, opacity)

    def ellipse(self, cx, cy, rx, ry, fill: Color, opacity: float = 1.0) -> None:
        pts = self._scaled([(cx - rx, cy - ry), (cx + rx, cy + ry)])
        self._fill(lambda d, v: d.ellipse([pts[0], pts[1]], fill=v), fill, opacity)

    def poly(self, points: List[Tuple[float, float]], fill: Color, opacity: float = 1.0) -> None:
        pts = self._scaled(points)
        self._fill(lambda d, v: d.polygon(pts, fill=v), fill, opacity)

    def line(self, x1, y1, x2, y2, color: Color, width: float) -> None:
        pts = self._scaled([(x1, y1), (x2, y2)])
        ImageDraw.Draw(self.img).line(pts, fill=_rgb(color) + (255,), width=max(1, int(width * SS)))

    def polyline(self, points, color: Color, width: float) -> None:
        pts = self._scaled(points)
        ImageDraw.Draw(self.img).line(pts, fill=_rgb(color) + (255,), width=max(1, int(width * SS)), joint="curve")

    def path(self, d: str, fill: Optional[Color] = None, stroke: Optional[Color] = None, width: float = 1.0) -> None:
        pts = _sample_path(d)
        if fill:
            self.poly(pts, fill)
        if stroke:
            self.polyline(pts, stroke, width)

    def text(self, x, y, s: str, color: Color = "#ffffff") -> None:
        font = ImageFont.load_default(size=12 * SS)
        ImageDraw.Draw(self.img).text((x * SS, y * SS), s, fill=_rgb(color) + (230,), font=font, anchor="ls")

    # -- composites -----------------------------------------------------------------------

    def blocks(self, x, y, w, h, cols, rows, fills: List[Color]) -> None:
        cw, ch = w / cols, h / rows
        for r in range(rows):
            for c in range(cols):
                fill = fills[(r * 3 + c * 2) % len(fills)]
                self.rect(x + c * cw + 1.5, y + r * ch + 1.5, cw - 3, ch - 3, fill)

    def vessel(self, cx, cy, length, width, angle, fill: Color) -> None:
        a = math.radians(angle)
        corners = [(-length / 2, -width / 2), (length / 2, -width / 2), (length / 2, width / 2), (-length / 2, width / 2)]
        pts = [(cx + px * math.cos(a) - py * math.sin(a), cy + px * math.sin(a) + py * math.cos(a)) for px, py in corners]
        self.poly(pts, fill)

    def tank(self, l, t, r, b, roof: Color) -> None:
        cx, cy = X((l + r) / 2), Y((t + b) / 2)
        rx, ry = X(r - l) / 2 - 4, Y(b - t) / 2 - 3
        self.ellipse(cx, cy + 5, rx, ry, "#3a3a3a", 0.55)
        self.ellipse(cx, cy, rx, ry, "#d8d8d2")
        self.ellipse(cx, cy, rx * 0.78, ry * 0.78, roof)
        self.ellipse(cx, cy, rx * 0.2, ry * 0.2, "#6b6b66")

    def finish(self, sar: bool) -> np.ndarray:
        rgb = self.img.convert("RGB").resize((W, H), Image.LANCZOS)
        arr = np.asarray(rgb, dtype=np.uint8)
        if sar:
            grey = (0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]).astype(np.uint8)
            return grey[None, ...]
        return np.transpose(arr, (2, 0, 1))


def _sample_path(d: str, steps: int = 16) -> List[Tuple[float, float]]:
    """Flatten the M/L/Q/Z subset of SVG path syntax used by the scenes into a polyline."""
    tokens = re.findall(r"[MLQZ]|-?\d+(?:\.\d+)?", d)
    pts: List[Tuple[float, float]] = []
    i = 0
    cmd = ""
    while i < len(tokens):
        if tokens[i] in "MLQZ":
            cmd = tokens[i]
            i += 1
            if cmd == "Z":
                continue
        if cmd in ("M", "L"):
            pts.append((float(tokens[i]), float(tokens[i + 1])))
            i += 2
        elif cmd == "Q":
            cx, cy, x, y = (float(v) for v in tokens[i:i + 4])
            x0, y0 = pts[-1]
            for s in range(1, steps + 1):
                t = s / steps
                pts.append(((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x,
                            (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y))
            i += 4
        else:
            raise ValueError(f"unsupported path command in {d!r}")
    return pts


# ---------------------------------------------------------------------------------------------
# Scenes (ported from frontend/src/data/mockImagery.ts; keep the two in step)
# ---------------------------------------------------------------------------------------------

CHANNEL = [(0, -89), (600, 253), (600, 393), (0, 51)]
V1 = dict(cx=X(33.3), cy=Y(23.5), length=105, width=28, angle=25)
V2 = dict(cx=X(62.3), cy=Y(47.8), length=115, width=30, angle=25)
V3 = dict(cx=X(19.3), cy=Y(71.6), length=70, width=22, angle=20)
COMPOUND_HARBOUR = "M0 0 L100 0 Q 110 200 90 330 Q 300 350 380 320 L600 330 L600 400 L0 400 Z"


def scene_a() -> Canvas:
    c = Canvas()
    c.rect(0, 0, W, H, "#8b8674")
    c.poly([(0, 255), (240, 255), (320, 285), (390, 335), (400, 400), (0, 400)], "url(#water)")
    c.polyline([(0, 255), (240, 255), (320, 285), (390, 335), (400, 400)], "#c8c4b4", 5)
    c.rect(405, 300, 195, 100, "#7a7a74")
    c.blocks(410, 305, 185, 90, 9, 4, CONTAINER_COLORS)
    c.line(330, 292, 392, 338, "#e6b422", 4)
    c.line(352, 305, 398, 342, "#e6b422", 4)
    c.rect(80, 70, 480, 190, "#9a9684", 0.55)
    c.path("M160 131 L301 149 L438 243", stroke="#5b5b56", width=3)
    c.tank(18.4, 24.1, 34.8, 41.5, "#e9e9e4")
    c.tank(42.1, 28.5, 58.2, 45.9, "#b9b9b0")
    c.tank(65.0, 52.0, 81.2, 69.4, "#cfcfc6")
    c.path("M0 60 L600 90", stroke="#d6d2c4", width=7)
    c.text(20, 30, "OPTICAL [Cartosat-2S] 0.65m GSD | BANDS: RGB-NIR")
    return c


def _temporal_base(developed: bool) -> Canvas:
    c = Canvas()
    c.rect(0, 0, W, H, "#7c7560")
    c.path("M0 0 L205 0 Q 222 120 210 220 Q 200 320 215 400 L0 400 Z", fill="url(#water)")
    c.rect(215, 250, 190, 120, "#8f8b7c")
    c.blocks(225, 258, 170, 100, 6, 3, ["#a8a496", "#76736a"])
    if developed:
        c.rect(X(35), Y(22), X(27), Y(32), "#9a9a94")
        c.line(X(37), Y(30), X(60), Y(30), "#3a3a3a", 3)
        c.line(X(37), Y(42), X(60), Y(42), "#3a3a3a", 3)
        c.rect(X(68), Y(45), X(20.5), Y(27), "#c9c9c2")
        c.blocks(X(69), Y(47), X(18.5), Y(23), 6, 4, CONTAINER_COLORS)
    else:
        c.rect(X(35), Y(22), X(27), Y(32), "#6f6a55")
        c.rect(X(68), Y(45), X(20.5), Y(27), "#8a8462")
        c.ellipse(X(78), Y(58), 40, 24, "#5f7a3d", 0.7)
    return c


def scene_t1() -> Canvas:
    c = _temporal_base(False)
    c.text(20, 30, "OBSERVATION T1 (2023-03-15) - BASELINE")
    return c


def scene_t2() -> Canvas:
    c = _temporal_base(True)
    c.text(20, 30, "OBSERVATION T2 (2025-01-20) - CURRENT", "#38bdf8")
    return c


def port_optical() -> Canvas:
    c = Canvas()
    c.rect(0, 0, W, H, "#8b8674")
    c.poly(CHANNEL, "url(#water)")
    c.ellipse(V3["cx"], V3["cy"], 62, 36, "url(#water)")
    c.poly([(60, -40), (600, 270), (600, 290), (60, -20)], "#b9b5a5", 0.8)
    c.blocks(380, 280, 200, 100, 8, 4, ["#a8a496", "#76736a", "#8a4d3b"])
    c.rect(410, 300, 160, 80, "#7a7a74")
    c.blocks(414, 304, 152, 72, 8, 3, CONTAINER_COLORS)
    c.vessel(**V1, fill="#2f3a48")
    c.vessel(**V2, fill="#5b3a2a")
    c.vessel(**V3, fill="#3a4a3a")
    c.ellipse(V3["cx"], V3["cy"], 78, 44, "#f4f6f8", 0.93)
    c.ellipse(V3["cx"] + 34, V3["cy"] - 14, 46, 28, "#ffffff", 0.9)
    c.ellipse(V3["cx"] - 40, V3["cy"] + 12, 40, 24, "#eef1f4", 0.9)
    c.text(20, 30, "OPTICAL [Sentinel-2 / Cartosat-2S] | BANDS: RGB-NIR | CLOUD 42%")
    return c


def port_sar() -> Canvas:
    c = Canvas()
    c.rect(0, 0, W, H, "#2a2a2a")
    c.rect(0, 0, W, H, "#444444", 0.25)
    c.poly(CHANNEL, "#050505")
    c.ellipse(V3["cx"], V3["cy"], 62, 36, "#030303")
    c.poly([(60, -40), (600, 270), (600, 290), (60, -20)], "#e2e2e2", 0.85)
    c.blocks(380, 280, 200, 100, 8, 4, ["#d6d6d6", "#e8e8e8", "#bdbdbd"])
    c.rect(410, 300, 160, 80, "#9a9a9a", 0.6)
    for v in (V1, V2, V3):
        c.vessel(**v, fill="#f2f2f2")
    c.text(20, 30, "SAR [RISAT-1A / Sentinel-1] C-Band VV/VH | BACKSCATTER dB", "#38bdf8")
    return c


def compound_optical() -> Canvas:
    c = Canvas()
    c.rect(0, 0, W, H, "#8b8674")
    c.path(COMPOUND_HARBOUR, fill="url(#water)")
    c.rect(X(20), Y(15), X(38), Y(33), "#9a9686")
    c.blocks(X(20) + 4, Y(15) + 4, X(38) - 8, Y(33) - 8, 9, 5, ["#a8a496", "#76736a", "#8a4d3b", "#b9b5a5"])
    c.rect(X(68), Y(45), X(20.5), Y(27), "#d4d4cc")
    c.blocks(X(69), Y(47), X(18.5), Y(23), 6, 4, CONTAINER_COLORS)
    c.line(X(58), Y(40), X(68), Y(55), "#4c4c48", 5)
    c.text(20, 30, "OPTICAL [Cartosat-2S] 0.65m GSD | BANDS: RGB-NIR")
    return c


def compound_sar() -> Canvas:
    c = Canvas()
    c.rect(0, 0, W, H, "#2a2a2a")
    c.rect(0, 0, W, H, "#444444", 0.25)
    c.path(COMPOUND_HARBOUR, fill="#050505")
    c.rect(X(20), Y(15), X(38), Y(33), "#8a8a8a", 0.8)
    c.blocks(X(20) + 4, Y(15) + 4, X(38) - 8, Y(33) - 8, 9, 5, ["#e2e2e2", "#d6d6d6", "#f0f0f0"])
    c.rect(X(68), Y(45), X(20.5), Y(27), "#6a6a6a", 0.7)
    c.text(20, 30, "SAR [RISAT-1A] C-Band Dual-Pol | BACKSCATTER dB", "#38bdf8")
    return c


# ---------------------------------------------------------------------------------------------
# Raster specs
# ---------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class RasterSpec:
    filename: str
    scene: callable
    sar: bool
    epsg: int
    gsd: float  # metres per pixel
    extent_m: Tuple[float, float]  # ground width, height covered; shared by a pair so footprints coincide
    centre_lonlat: Tuple[float, float]
    platform: str
    acquired: Optional[str]


BHOPAL = (77.41, 23.26)
BENGALURU = (77.59, 12.97)
ASSAM = (91.74, 26.14)
HYDERABAD = (78.49, 17.39)

SPECS: List[RasterSpec] = [
    RasterSpec("Cartosat2S_Scene_Bhopal.tif", scene_a, False, 32643, 0.65, (390, 260), BHOPAL, "Cartosat-2S", "2024-11-04T05:32:10Z"),
    RasterSpec("Sentinel2_Bengaluru_2023.tif", scene_t1, False, 32643, 10.0, (6000, 4000), BENGALURU, "Sentinel-2", "2023-03-15T05:10:00Z"),
    RasterSpec("Sentinel2_Bengaluru_2025.tif", scene_t2, False, 32643, 10.0, (6000, 4000), BENGALURU, "Sentinel-2", "2025-01-20T05:12:00Z"),
    RasterSpec("Sentinel2_RGBNIR_Assam.tif", port_optical, False, 32646, 10.0, (6000, 4000), ASSAM, "Sentinel-2", "2024-07-12T04:20:00Z"),
    RasterSpec("Sentinel1_SAR_Assam_C_Band.tif", port_sar, True, 32646, 10.0, (6000, 4000), ASSAM, "Sentinel-1", "2024-07-12T12:45:00Z"),
    RasterSpec("Cartosat2S_Hyderabad.tif", compound_optical, False, 32644, 0.65, (390, 260), HYDERABAD, "Cartosat-2S", None),
    RasterSpec("RISAT1_Hyderabad_DualPol.tif", compound_sar, True, 32644, 1.0, (390, 260), HYDERABAD, "RISAT-1", None),
]


def write_raster(spec: RasterSpec, out_dir: Path) -> Path:
    data = spec.scene().finish(spec.sar)
    width, height = round(spec.extent_m[0] / spec.gsd), round(spec.extent_m[1] / spec.gsd)
    if (data.shape[2], data.shape[1]) != (width, height):
        # Same ground extent, coarser pixels (a SAR product at 1 m beside a 0.65 m optical scene).
        img = Image.fromarray(data[0] if spec.sar else np.transpose(data, (1, 2, 0)))
        img = img.resize((width, height), Image.LANCZOS)
        arr = np.asarray(img, dtype=np.uint8)
        data = arr[None, ...] if spec.sar else np.transpose(arr, (2, 0, 1))

    east, north = warp_transform("EPSG:4326", f"EPSG:{spec.epsg}", [spec.centre_lonlat[0]], [spec.centre_lonlat[1]])
    west_edge = east[0] - spec.extent_m[0] / 2
    north_edge = north[0] + spec.extent_m[1] / 2

    path = out_dir / spec.filename
    profile = dict(
        driver="GTiff", dtype="uint8", count=data.shape[0], height=height, width=width,
        crs=f"EPSG:{spec.epsg}", transform=from_origin(west_edge, north_edge, spec.gsd, spec.gsd),
        compress="lzw",
    )
    if data.shape[0] == 3:
        profile["photometric"] = "RGB"
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data)
        tags = {"PLATFORM": spec.platform, "DEMO_NOTE": DEMO_NOTE}
        if spec.acquired:
            tags["ACQUISITION_DATE"] = spec.acquired
        dst.update_tags(**tags)
    return path


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for spec in SPECS:
        path = write_raster(spec, OUT_DIR)
        with rasterio.open(path) as src:
            print(f"{path.name:36s} {src.width}x{src.height} x{src.count}  {src.crs}  "
                  f"{abs(src.transform.a):g} m  {path.stat().st_size / 1024:6.0f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
