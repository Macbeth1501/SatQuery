"""B1 (full): build the split, quality and box-row index over the ingested pool (ML_PLAN phase 1).

    .venv-ml/Scripts/python.exe ml/b1_index.py split      # official split + 2-cell buffer (parquet only)
    .venv-ml/Scripts/python.exe ml/b1_index.py quality    # 5%-cloud cap over data/b1_full/s2 (needs ingestion done)
    .venv-ml/Scripts/python.exe ml/b1_index.py boxes      # bounding-box rows, in the confirmed x0y0x1y1 convention

Kept as an index over the store `ml/b1_full.py` already built, not a rebuild: `data/b1_full/{s2,s1}` hold every
patch with no split or filter applied, so changing a rule here never means re-reading 117 GB of archives.

`split` reuses `ml/b1_slice.py`'s exact rule, at full scale: BigEarthNet's 4 official labels (train, validation,
test, bench) kept as given, plus BUFFER_CELLS -- no `train` patch lies within that many 1.2 km grid cells of a
`validation` or `bench` patch (`ml/b1_slice.py`'s own docstring explains why: the official split is not
geographic, so an untouched buffer leaks). **`test` is not buffered against**, matching `b1_slice.py`'s own
choice; nothing in this project has scored against `test` yet (`bench_hard` uses `bench`), so this is flagged in
the report rather than silently assumed forever.

`quality` is the plan's 5%-cloud cap that replaced the Development Plan's degenerate "drop the bottom quartile"
rule (see `b1_slice.py`): a patch is dropped if its cloud-like share, from `QUALITY.py`'s brightness proxy on the
stored S2 RGB, exceeds CLOUD_LIKE_MAX_SHARE. Logged as `pairs_in`/`pairs_kept` per split, as the plan asks.

`boxes` pulls every `type == "bounding box"` row and keeps only patches present in the S2 store, converting
nothing: the parquet's own `[x0 y0, x1 y1]` is already the convention B6 needs (confirmed by `ml/b1_boxes.py`).
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PARQUET = ROOT / "data" / "BigEarthNet" / "BigEarthNet.txt" / "BigEarthNet.txt.parquet"
POOL = ROOT / "data" / "b1_full"
OUT_DIR = ROOT / "data" / "b1_full"
BUFFER_CELLS = 2  # same as ml/b1_slice.py: Chebyshev distance in 1.2 km grid cells
CLOUD_LIKE_MEAN_DN = 2500  # same proxy and threshold as ml/b1_slice.py
CLOUD_LIKE_MAX_SHARE = 0.05
BUFFERED_AGAINST = ("validation", "bench")  # test is not buffered against; see the module docstring


def load_index():
    import pandas as pd
    import pyarrow.parquet as pq

    cols = ["patch_id", "split"]
    df = pq.read_table(PARQUET, columns=cols).to_pandas().drop_duplicates("patch_id")
    parts = df.patch_id.str.rsplit("_", n=2, expand=True)
    df["scene"], df["row"], df["col"] = parts[0], parts[1].astype(int), parts[2].astype(int)
    df["tile"] = df.scene.str.extract(r"_(T\d\d[A-Z]{3})$")[0]
    return df


def neighbourhood(scene, row, col, k):
    return {(scene, r, c) for r in range(row - k, row + k + 1) for c in range(col - k, col + k + 1)}


def cmd_split(_args):
    df = load_index()
    reference = df[df.split.isin(BUFFERED_AGAINST)]
    blocked = set()
    for s, r, c in zip(reference.scene, reference.row, reference.col):
        blocked |= neighbourhood(s, r, c, BUFFER_CELLS)

    train = df[df.split == "train"]
    in_buffer = np.array([(s, r, c) in blocked for s, r, c in zip(train.scene, train.row, train.col)])
    assignment = dict(zip(df.patch_id, df.split))
    for patch_id in train.patch_id[in_buffer]:
        assignment[patch_id] = "train_buffered_out"  # official train, but within BUFFER_CELLS of val/bench

    (OUT_DIR / "split.json").write_text(json.dumps(assignment, indent=0), encoding="utf-8")
    report = {
        "buffer_cells": BUFFER_CELLS,
        "buffered_against": list(BUFFERED_AGAINST),
        "test_not_buffered_note": "matches ml/b1_slice.py; nothing has scored against 'test' yet (bench_hard "
                                  "uses 'bench'); revisit if that changes",
        "counts": {k: int((df.split == k).sum()) for k in ("train", "validation", "test", "bench")},
        "train_patches_inside_buffer": int(in_buffer.sum()),
        "train_patches_usable": int((~in_buffer).sum()),
        "total_patches": len(df),
        "built_on": time.strftime("%Y-%m-%d %H:%M"),
    }
    (OUT_DIR / "split_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


def quality(rgb_uint16):
    """(nodata_share, cloud_like_share) on a (3, h, w) B04/B03/B02 uint16 crop, same proxy as ml/b1_slice.py."""
    dn = np.moveaxis(rgb_uint16, 0, -1)
    nodata = float(np.mean((dn == 0).all(axis=-1)))
    cloud_like = float(np.mean(dn.astype("float32").mean(axis=-1) >= CLOUD_LIKE_MEAN_DN))
    return nodata, cloud_like


def cmd_quality(_args):
    import lmdb

    if not (POOL / "s2" / "data.mdb").is_file():
        sys.exit("data/b1_full/s2 does not exist yet: run `ml/b1_full.py ingest --modality s2` first")
    split = json.loads((OUT_DIR / "split.json").read_text(encoding="utf-8")) if (OUT_DIR / "split.json").is_file() \
        else {}
    env = lmdb.open(str(POOL / "s2"), readonly=True, lock=False, readahead=False, map_size=1 << 40)
    kept, dropped_nodata, dropped_cloud = [], [], []
    by_split_in, by_split_kept = {}, {}
    start = time.perf_counter()
    with env.begin() as txn:
        for i, (key, value) in enumerate(txn.cursor()):
            patch_id = key.decode()
            rgb = np.frombuffer(value, np.uint16).reshape(4, 120, 120)[[0, 1, 2]]  # stored order: B04 B03 B02 B08
            nodata, cloud = quality(rgb)
            group = split.get(patch_id, "unknown")
            by_split_in[group] = by_split_in.get(group, 0) + 1
            if nodata > 0.01:
                dropped_nodata.append(patch_id)
            elif cloud > CLOUD_LIKE_MAX_SHARE:
                dropped_cloud.append(patch_id)
            else:
                kept.append(patch_id)
                by_split_kept[group] = by_split_kept.get(group, 0) + 1
            if (i + 1) % 20000 == 0:
                print(f"quality: {i + 1:,} patches, {time.perf_counter() - start:.0f} s", flush=True)
    env.close()

    (OUT_DIR / "quality_kept.json").write_text(json.dumps(kept), encoding="utf-8")
    report = {
        "cloud_like_mean_dn": CLOUD_LIKE_MEAN_DN,
        "cloud_like_max_share": CLOUD_LIKE_MAX_SHARE,
        "nodata_max_share": 0.01,
        "pairs_in": by_split_in,
        "pairs_kept": by_split_kept,
        "dropped_nodata": len(dropped_nodata),
        "dropped_cloud": len(dropped_cloud),
        "total_in": len(kept) + len(dropped_nodata) + len(dropped_cloud),
        "seconds": round(time.perf_counter() - start, 1),
        "built_on": time.strftime("%Y-%m-%d %H:%M"),
    }
    (OUT_DIR / "quality_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


def cmd_boxes(_args):
    import pyarrow.parquet as pq

    if not (POOL / "s2" / "data.mdb").is_file():
        sys.exit("data/b1_full/s2 does not exist yet: run `ml/b1_full.py ingest --modality s2` first")
    import lmdb

    env = lmdb.open(str(POOL / "s2"), readonly=True, lock=False, readahead=False, map_size=1 << 40)
    with env.begin() as txn:
        have = {k.decode() for k, _ in txn.cursor()}
    env.close()

    df = pq.read_table(PARQUET, columns=["patch_id", "input", "output", "type", "category"]).to_pandas()
    boxes = df[(df.type == "bounding box") & df.patch_id.isin(have)]
    rows = [{"patch_id": r.patch_id, "prompt": r.input, "box": r.output, "category": r.category}
            for r in boxes.itertuples()]
    (OUT_DIR / "boxes.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    report = {"box_convention": "x0y0x1y1, unit interval, origin top-left (confirmed by ml/b1_boxes.py)",
              "rows_total": len(df[df.type == "bounding box"]), "rows_with_a_stored_patch": len(rows),
              "by_category": {k: int(v) for k, v in boxes.category.value_counts().items()},
              "built_on": time.strftime("%Y-%m-%d %H:%M")}
    (OUT_DIR / "boxes_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("split").set_defaults(func=cmd_split)
    sub.add_parser("quality").set_defaults(func=cmd_quality)
    sub.add_parser("boxes").set_defaults(func=cmd_boxes)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
