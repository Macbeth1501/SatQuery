"""Build the real BigEarthNet samples the website's live-model presets serve from frontend/public/real/.

Unlike tools/make_demo_rasters.py, nothing here is drawn: the picture is a real Sentinel-2 L2A patch from
BigEarthNet, rendered from its B04/B03/B02 bands with ml/b1_slice.render() -- the same function, and so the same
pixels, the B5 adapter was trained and evaluated on (the output is checked against the evaluation PNG). The
GeoTIFF keeps the patch's own CRS and geotransform from its B04 band, so the backend reads real georeferencing.

    python tools/make_real_sample.py

Writes, for each patch in PATCH_IDS:
  * bigearthnet_<tile>_<row>_<col>.tif  3-band uint8 GeoTIFF (what the website uploads);
  * bigearthnet_<tile>_<row>_<col>.png  the same pixels as a PNG (what the website shows);
and frontend/src/data/realSamples.json with every patch's facts and its bench_hard questions and reference answers.

How the patches were chosen (2026-09-21): held-out patches only, i.e. their Sentinel tile is in neither
data/b1_v2/train.jsonl nor validation.jsonl (checked again below), with at least 3 bench_hard questions, all of
which the run-2 adapter answers correctly when asked through ml/serve_vqa.py. They were picked because the model
does well on them, for variety of country and season; they are samples, not a measure of accuracy.
"""
import glob
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml"))
from b1_slice import read_rgb, render  # noqa: E402

PATCH_IDS = [
    "S2B_MSIL2A_20171112T114339_N9999_R123_T29UPU_55_58",  # Ireland, autumn: 5 questions
    "S2B_MSIL2A_20180421T114349_N9999_R123_T29UPU_38_37",  # Ireland, spring: 5
    "S2A_MSIL2A_20180413T095031_N9999_R079_T34UEG_28_34",  # Lithuania, spring: 6
    "S2A_MSIL2A_20170803T094031_N9999_R036_T34TCR_36_25",  # Serbia, summer: 4
    "S2A_MSIL2A_20171121T112351_N9999_R037_T29SND_42_38",  # Portugal, autumn: 3
]
BENCH_S2 = ROOT / "data" / "BigEarthNet" / "bench_subset" / "S2"
BENCH = ROOT / "data" / "b1_v2" / "bench_hard.jsonl"
EVAL_DIR = ROOT / "data" / "b1_v2" / "bench_images"
TRAINING = [ROOT / "data" / "b1_v2" / "train.jsonl", ROOT / "data" / "b1_v2" / "validation.jsonl"]
OUT_DIR = ROOT / "frontend" / "public" / "real"
# Imported by the frontend, which cannot import from public/, and read by tests/test_real_model.py.
SAMPLE_JSON = ROOT / "frontend" / "src" / "data" / "realSamples.json"

SOURCE_NOTE = (
    "Real Sentinel-2 L2A patch from BigEarthNet (bands B04, B03, B02; 10 m), rendered as true colour by "
    "ml/b1_slice.render(). Not synthetic."
)


def band_paths(patch_id):
    paths = {}
    for band in ("B02", "B03", "B04"):
        hits = glob.glob(str(BENCH_S2 / "**" / f"{patch_id}_{band}.tif"), recursive=True)
        if not hits:
            sys.exit(f"band {band} of {patch_id} not found under {BENCH_S2}")
        paths[band] = Path(hits[0])
    return paths


def acquisition(patch_id):
    """'S2B_MSIL2A_20171112T114339_...' -> ('Sentinel-2B', '2017-11-12T11:43:39Z')."""
    platform, _, stamp = patch_id.split("_")[:3]
    return (f"Sentinel-2{platform[-1]}",
            f"{stamp[0:4]}-{stamp[4:6]}-{stamp[6:8]}T{stamp[9:11]}:{stamp[11:13]}:{stamp[13:15]}Z")


def tile(patch_id):
    return patch_id.split("_")[5]


def training_tiles():
    tiles = set()
    for path in TRAINING:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                tiles.add(tile(json.loads(line)["patch_id"]))
    return tiles


def build(patch_id, rows):
    paths = band_paths(patch_id)
    image = render(read_rgb(paths))
    pixels = np.asarray(image, dtype=np.uint8)

    eval_png = EVAL_DIR / f"{patch_id}.png"
    if eval_png.exists() and not np.array_equal(pixels, np.asarray(Image.open(eval_png).convert("RGB"))):
        sys.exit(f"rendered pixels differ from the evaluation image {eval_png}; refusing to write")

    tile_rc = "_".join(patch_id.split("_")[-3:])
    tif, png = OUT_DIR / f"bigearthnet_{tile_rc}.tif", OUT_DIR / f"bigearthnet_{tile_rc}.png"
    platform, acquired = acquisition(patch_id)

    with rasterio.open(paths["B04"]) as src:
        crs, transform, gsd = src.crs, src.transform, abs(src.transform.a)
    profile = dict(driver="GTiff", dtype="uint8", count=3, height=pixels.shape[0], width=pixels.shape[1],
                   crs=crs, transform=transform, compress="lzw", photometric="RGB")
    with rasterio.open(tif, "w", **profile) as dst:
        dst.write(np.transpose(pixels, (2, 0, 1)))
        dst.update_tags(PLATFORM=platform, ACQUISITION_DATE=acquired, SOURCE_NOTE=SOURCE_NOTE,
                        BIGEARTHNET_PATCH=patch_id)
    image.save(png)

    # The website uploads the GeoTIFF; the backend, the overlay renderer and the model server all need it to
    # decode in Pillow as well as in rasterio (the same rule tests/test_demo_rasters.py applies).
    with Image.open(tif) as check:
        assert np.array_equal(np.asarray(check.convert("RGB")), pixels), "Pillow reads different pixels"
    with rasterio.open(tif) as check:
        assert check.crs == crs and check.count == 3

    mine = [r for r in rows if r["patch_id"] == patch_id]
    print(f"{tif.name}: {pixels.shape[1]}x{pixels.shape[0]} px, {crs}, {gsd} m, {platform} {acquired}, "
          f"{mine[0]['country']}, {len(mine)} questions")
    return {
        "id": tile_rc,
        "patchId": patch_id,
        "tile": tile(patch_id),
        "platform": platform,
        "acquired": acquired,
        "country": mine[0]["country"],
        "season": mine[0]["season"],
        "widthPx": int(pixels.shape[1]),
        "heightPx": int(pixels.shape[0]),
        "gsdMeters": gsd,
        "crs": str(crs),
        "rasterFile": tif.name,
        "previewFile": png.name,
        "questions": [{"question": r["question"], "answer": r["answer"], "type": r["type"], "category": r["category"]}
                      for r in mine],
    }


def main():
    seen = training_tiles()
    leaked = [p for p in PATCH_IDS if tile(p) in seen]
    if leaked:
        sys.exit(f"these patches' tiles appear in training: {leaked}")
    rows = [json.loads(line) for line in BENCH.read_text(encoding="utf-8").splitlines() if line.strip()]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    samples = [build(p, rows) for p in PATCH_IDS]
    SAMPLE_JSON.write_text(json.dumps({"samples": samples}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(samples)} samples, {sum(len(s['questions']) for s in samples)} questions -> {SAMPLE_JSON}")


if __name__ == "__main__":
    main()
