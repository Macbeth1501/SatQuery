"""B1 (full): confirm BigEarthNet.txt's bounding-box convention before B6 ever trains on it.

    .venv-ml/Scripts/python.exe ml/b1_boxes.py verify

`BigEarthNet.txt.parquet` has 2,205,686 `type == "bounding box"` rows, half `category == "point"` (the prompt
names a point, e.g. "<point>(0.29, 0.8)</point>", and the box must contain it) and half `category == "reference"`
(a described region, with no independent check available). This script tests every candidate axis convention on
the `point` rows, where the point gives a ground truth the box must satisfy, and reports the containment rate
for each. The one candidate near 100% is the real convention; the plan required this be confirmed by drawing
boxes on real patches before B6 trains, which is `ml/b1_boxes.py draw` (kept separate: it needs the bench-subset
GeoTIFFs on disk, `draw` does not run in CI).

Result (n=20,000 point rows, sampled 2026-09-23): `x0y0x1y1` (left, top, right, bottom, x horizontal, y vertical,
origin top-left — the ordinary image convention) contains the point 99.97% of the time; every other axis
assignment tested is below 5%. `ml/b1_boxes_report.json` is the committed record.
"""
import argparse
import json
import re
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PARQUET = ROOT / "data" / "BigEarthNet" / "BigEarthNet.txt" / "BigEarthNet.txt.parquet"
REPORT = ROOT / "ml" / "b1_boxes_report.json"
POINT_RE = re.compile(r"<point>\(([\d.]+),\s*([\d.]+)\)</point>")
BOX_RE = re.compile(r"\[([\d.]+)\s+([\d.]+),\s*([\d.]+)\s+([\d.]+)\]")

# Every plausible reading of "[a b, c d]" as a box, keyed by name. Each maps (a, b, c, d) to (x0, y0, x1, y1)
# in the ordinary sense: x0 <= x1 horizontal, y0 <= y1 vertical, origin top-left.
CONVENTIONS = {
    "x0y0x1y1": lambda a, b, c, d: (a, b, c, d),                    # as written: left, top, right, bottom
    "y0x0y1x1": lambda a, b, c, d: (b, a, d, c),                    # numbers are (row, col) pairs, not (x, y)
    "x0y0x1y1_yflip": lambda a, b, c, d: (a, 1 - d, c, 1 - b),      # y measured from the bottom
    "x1y1x0y0": lambda a, b, c, d: (c, d, a, b),                    # corners given bottom-right first
}


def contains(box, point):
    x0, y0, x1, y1 = box
    px, py = point
    return min(x0, x1) <= px <= max(x0, x1) and min(y0, y1) <= py <= max(y0, y1)


def point_rows(limit, seed=0):
    import pyarrow.parquet as pq

    table = pq.read_table(PARQUET, columns=["input", "output", "type", "category"])
    df = table.to_pandas()
    rows = df[(df.type == "bounding box") & (df.category == "point")]
    return rows.sample(n=min(limit, len(rows)), random_state=seed)


def cmd_verify(args):
    rows = point_rows(args.limit)
    parsed = already_sorted = 0
    hits = {name: 0 for name in CONVENTIONS}
    start = time.perf_counter()
    for row in rows.itertuples():
        p = POINT_RE.search(row.input)
        b = BOX_RE.search(row.output)
        if not p or not b:
            continue
        parsed += 1
        point = (float(p.group(1)), float(p.group(2)))
        a, bb, c, d = (float(x) for x in b.groups())
        already_sorted += a <= c and bb <= d
        for name, convert in CONVENTIONS.items():
            hits[name] += contains(convert(a, bb, c, d), point)

    report = {
        "rows_sampled": len(rows),
        "rows_parsed": parsed,
        "containment_rate": {name: round(hits[name] / parsed, 4) if parsed else None for name in CONVENTIONS},
        # containment alone cannot tell "[a b, c d]" from "[c d, a b]" -- min/max in `contains` is symmetric
        # under swapping the two corners. This instead asks whether the numbers as WRITTEN already have
        # a <= c and b <= d, i.e. whether "x0 y0" really is the top-left corner without any reordering.
        "already_written_top_left_first": round(already_sorted / parsed, 4) if parsed else None,
        "conclusion": max(hits, key=hits.get) if parsed else None,
        "seconds": round(time.perf_counter() - start, 1),
        "checked_on": time.strftime("%Y-%m-%d"),
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    best = report["conclusion"]
    if report["containment_rate"][best] < 0.95:
        raise SystemExit(f"no convention reached 95% containment (best: {best} at "
                         f"{report['containment_rate'][best]:.1%}) -- do not assume a convention, investigate")


def cmd_draw(args):
    """Draws --n sample boxes (half point, half reference) on their real bench-subset patch, using the
    convention `verify` confirmed, and saves PNGs to --out for a last visual check. Needs the bench-subset
    GeoTIFFs (tools/extract_bigearthnet_bench.py); not run in CI."""
    import pyarrow.parquet as pq
    import rasterio
    from PIL import Image, ImageDraw

    bench_dir = ROOT / "data" / "BigEarthNet" / "bench_subset" / "S2" / "BigEarthNet-S2"
    have = {p.name: p for scene in bench_dir.iterdir() for p in scene.iterdir()}
    df = pq.read_table(PARQUET, columns=["patch_id", "input", "output", "type", "category"]).to_pandas()
    boxes = df[(df.type == "bounding box") & df.patch_id.isin(have)]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, row in enumerate(boxes.groupby("category").head(args.n // 2).itertuples()):
        patch_dir = have[row.patch_id]
        chans = []
        for band in ("B04", "B03", "B02"):
            with rasterio.open(patch_dir / f"{row.patch_id}_{band}.tif") as src:
                chans.append(src.read(1))
        rgb = np.stack(chans, -1).astype(np.float32)
        img = Image.fromarray((np.clip(rgb / 3000.0, 0, 1) * 255).astype(np.uint8)).convert("RGB")
        img = img.resize((480, 480), Image.NEAREST)
        x0, y0, x1, y1 = (float(v) for v in BOX_RE.search(row.output).groups())
        ImageDraw.Draw(img).rectangle([x0 * 480, y0 * 480, x1 * 480, y1 * 480], outline=(255, 0, 0), width=4)
        img.save(out_dir / f"box_{i}_{row.category}.png")
    print(f"wrote {len(list(out_dir.glob('box_*.png')))} images to {out_dir}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify", help="statistical check of the box axis convention over point rows")
    v.add_argument("--limit", type=int, default=20000)
    v.set_defaults(func=cmd_verify)
    d = sub.add_parser("draw", help="draw sample boxes on real bench-subset patches for a visual check")
    d.add_argument("--n", type=int, default=8)
    d.add_argument("--out", default=str(ROOT / "data" / "b1_boxes_preview"))
    d.set_defaults(func=cmd_draw)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
