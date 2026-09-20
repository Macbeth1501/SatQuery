"""B1 (thin): a small, reproducible training slice of BigEarthNet.txt for the B5 caption/VQA adapter.

This is deliberately not the full pool. Its job is to give the LoRA recipe something real to train on
so the recipe can be proven on a small run before anyone pays for a full-scale ingest.

    python ml/b1_slice.py select     # choose candidate patches (official split + spatial buffer)
    python ml/b1_slice.py extract    # stream the S2 archive once, keeping only B02/B03/B04 of candidates
    python ml/b1_slice.py build      # quality rule, annotation sampling, PNG renders, jsonl + report

Every rule that decides what is kept is a constant below, so the written rule and the code cannot
disagree. Counts at each stage go to ml/b1_slice_report.json, which is committed; the data itself goes
to data/b1_slice/, which is not.

THE OFFICIAL SPLIT IS NOT GEOGRAPHIC. The `split` column (train / validation / test / bench) assigns
whole patches, but 52 of the 54 Sentinel tiles appear in more than one split and 97.8% of patches have an
immediately adjacent neighbour, so neighbouring 1.2 km cells routinely land on opposite sides of a split.
We keep the official labels, as instructed, and add BUFFER_CELLS: no training patch lies within that many
grid cells of a validation-slice or bench patch. That removes the nearest leakage. It does not remove it
all: training and evaluation patches can still come from the same tile and acquisition date, so scores on
`validation` and `bench` remain optimistic relative to genuinely unseen regions.

Quality is scored from the pixels we have (BigEarthNet's own cloud and shadow masks are not in the
archive we downloaded), so the score is a proxy, and it is named as one in the report.
"""
import argparse
import hashlib
import json
import random
import sys
import tarfile
from collections import Counter
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import rasterio
import zstandard
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "BigEarthNet"
PARQUET = DATA / "BigEarthNet.txt" / "BigEarthNet.txt.parquet"
S2_ARCHIVE = DATA / "BigEarthNet-S2" / "BigEarthNet-S2.tar.zst"
WORK = ROOT / "data" / "b1_slice"
REPORT = ROOT / "ml" / "b1_slice_report.json"

# ---- the written rules -------------------------------------------------------------------------------
SEED = 20260920
N_TRAIN_CANDIDATES = 2100  # official `train` split, before the quality rule
N_VAL_CANDIDATES = 210  # official `validation` split, before the quality rule
BUFFER_CELLS = 2  # Chebyshev distance in 1.2 km grid cells kept between train and val/bench patches

# Image quality proxy, computed on the 120x120 B04/B03/B02 crop. NoData and cloud-like are separate hard caps.
NODATA_MAX_SHARE = 0.01  # hard drop: more than 1% of pixels have B02 = B03 = B04 = 0
CLOUD_LIKE_MEAN_DN = 2500  # a pixel is "cloud-like" when mean(B02, B03, B04) >= 2500 (about 0.25 reflectance)
CLOUD_LIKE_MAX_SHARE = 0.05  # hard drop: more than 5% of pixels are cloud-like
# The Development Plan says "drop the bottom quartile". Measured on the 2,100 train candidates that rule is
# degenerate: 75% of patches score exactly 0 and the 90th percentile is under 0.5%, so a quartile cut removes
# any patch with a single bright pixel (a roof, a sandbar) and breaks ties by input order. An absolute cap
# removes the 105 patches (5.0%) that are actually bright. Bright pixels can be snow, sand or roofs as well
# as cloud, which is why this is a proxy.

# Annotation sampling per kept patch. Bounding-box rows are excluded: grounding is B6 and is never
# joint-trained with VQA/captioning (Development Plan, B6).
PER_PATCH = {"captioning": 1, "binary": 4, "mcq": 4}
# Text rule: drop a question whose options include both "Fall" and "Autumn". They are synonyms, so the answer
# is one of two indistinguishable options and no image can support it. Measured: 242 of the 1,161 season
# questions in the train candidates (21%), and 127 of the 700 on bench.
def has_synonym_options(question):
    low = question.lower()
    return "fall" in low and "autumn" in low


# Fixed-scale true-colour render: DN / RGB_SCALE, clipped. A per-image stretch would erase brightness.
RGB_SCALE = 3000.0
# -------------------------------------------------------------------------------------------------------


def load_index():
    """One row per annotation, with the tile grid coordinates parsed from the patch id."""
    cols = ["ID", "patch_id", "s1_name", "input", "output", "type", "category", "split", "country", "season"]
    df = pq.read_table(PARQUET, columns=cols).to_pandas()
    parts = df.patch_id.str.rsplit("_", n=2, expand=True)
    df["scene"], df["row"], df["col"] = parts[0], parts[1].astype(int), parts[2].astype(int)
    df["tile"] = df.scene.str.extract(r"_(T\d\d[A-Z]{3})$")[0]
    return df


def patches_of(df, split):
    return df[df.split == split].drop_duplicates("patch_id")[["patch_id", "scene", "row", "col", "tile"]]


def neighbourhood(scene, row, col, k):
    return {(scene, r, c) for r in range(row - k, row + k + 1) for c in range(col - k, col + k + 1)}


def cmd_select(_args):
    df = load_index()
    bench = patches_of(df, "bench")
    val_all = patches_of(df, "validation")
    train_all = patches_of(df, "train")

    val = val_all.sample(n=N_VAL_CANDIDATES, random_state=SEED)
    reference = pd_concat(bench, val)
    blocked = set()
    for s, r, c in zip(reference.scene, reference.row, reference.col):
        blocked |= neighbourhood(s, r, c, BUFFER_CELLS)

    in_buffer = np.array([(s, r, c) in blocked for s, r, c in zip(train_all.scene, train_all.row, train_all.col)])
    eligible = train_all[~in_buffer]
    train = eligible.sample(n=N_TRAIN_CANDIDATES, random_state=SEED)

    WORK.mkdir(parents=True, exist_ok=True)
    selection = {
        "train": train.patch_id.tolist(),
        "validation": val.patch_id.tolist(),
    }
    (WORK / "candidates.json").write_text(json.dumps(selection, indent=1), encoding="utf-8")
    stats = {
        "official_train_patches": len(train_all),
        "train_patches_inside_buffer": int(in_buffer.sum()),
        "train_patches_eligible": len(eligible),
        "train_candidates": len(train),
        "validation_candidates": len(val),
        "buffer_cells": BUFFER_CELLS,
        "buffer_reference_patches": len(reference),
        "candidate_train_tiles": int(train.tile.nunique()),
        "candidate_train_tiles_shared_with_bench": int(len(set(train.tile) & set(bench.tile))),
    }
    (WORK / "select_stats.json").write_text(json.dumps(stats, indent=1), encoding="utf-8")
    print(json.dumps(stats, indent=1))


def pd_concat(*frames):
    import pandas as pd

    return pd.concat(frames, ignore_index=True)


def cmd_extract(_args):
    """One streaming pass over the S2 archive; keeps only B02/B03/B04 of the candidate patches."""
    cand = json.loads((WORK / "candidates.json").read_text(encoding="utf-8"))
    wanted = set(cand["train"]) | set(cand["validation"])
    dest = WORK / "raw_s2"
    dest.mkdir(parents=True, exist_ok=True)
    kept = scanned = 0
    with S2_ARCHIVE.open("rb") as fh:
        reader = zstandard.ZstdDecompressor().stream_reader(fh)
        with tarfile.open(fileobj=reader, mode="r|") as tar:
            for member in tar:
                scanned += 1
                if scanned % 500000 == 0:
                    print(f"scanned {scanned:,}, kept {kept:,}", flush=True)
                if not member.isfile() or not member.name.endswith(("_B02.tif", "_B03.tif", "_B04.tif")):
                    continue
                patch = Path(member.name).parent.name
                if patch in wanted:
                    tar.extract(member, dest)
                    kept += 1
    print(f"done: scanned {scanned:,} members, kept {kept:,} files for {len(wanted)} candidate patches")


_BAND_INDEX = {}


def band_paths(patch_id):
    """Paths of the three extracted bands of a patch, or None if any is missing."""
    if not _BAND_INDEX:
        _BAND_INDEX.update({p.stem: p for p in (WORK / "raw_s2").rglob("*.tif")})
    paths = {band: _BAND_INDEX.get(f"{patch_id}_{band}") for band in ("B02", "B03", "B04")}
    return paths if all(paths.values()) else None


def read_rgb(paths):
    chans = []
    for band in ("B04", "B03", "B02"):
        with rasterio.open(paths[band]) as src:
            chans.append(src.read(1))
    return np.stack(chans, -1)  # uint16 DN, H x W x 3 in R, G, B order


def quality(dn):
    nodata = float(np.mean((dn == 0).all(axis=-1)))
    cloud_like = float(np.mean(dn.astype("float32").mean(axis=-1) >= CLOUD_LIKE_MEAN_DN))
    return nodata, cloud_like


def render(dn):
    return Image.fromarray((np.clip(dn.astype("float32") / RGB_SCALE, 0, 1) * 255).astype(np.uint8))


def sample_rows(rows, n, rng):
    """Up to n rows spread across categories round-robin, so one category cannot crowd out the rest."""
    buckets = {}
    for row in rows.itertuples():
        buckets.setdefault(row.category, []).append(row)
    for b in buckets.values():
        rng.shuffle(b)
    order = sorted(buckets)
    rng.shuffle(order)
    picked = []
    while len(picked) < n and any(buckets.values()):
        for cat in order:
            if buckets[cat] and len(picked) < n:
                picked.append(buckets[cat].pop())
    return picked


def cmd_build(_args):
    df = load_index()
    cand = json.loads((WORK / "candidates.json").read_text(encoding="utf-8"))
    img_dir = WORK / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "rules": {
            "seed": SEED, "buffer_cells": BUFFER_CELLS, "nodata_max_share": NODATA_MAX_SHARE,
            "cloud_like_mean_dn": CLOUD_LIKE_MEAN_DN, "cloud_like_max_share": CLOUD_LIKE_MAX_SHARE,
            "per_patch": PER_PATCH, "rgb_scale": RGB_SCALE, "drop_fall_and_autumn_options": True,
            "quality_rule": "drop a patch if nodata share > nodata_max_share or cloud-like share > cloud_like_max_share; "
                            "a pixel-brightness PROXY, not BigEarthNet's cloud/shadow masks, which are not in "
                            "the archive used. Replaces the plan's 'bottom quartile', which is degenerate on "
                            "this data (see the comment in ml/b1_slice.py).",
        },
        "select": json.loads((WORK / "select_stats.json").read_text(encoding="utf-8")),
        "splits": {},
    }
    meta = df.drop_duplicates("patch_id").set_index("patch_id")

    for split, official in (("train", "train"), ("validation", "validation")):
        patch_ids = cand[split]
        scored, missing = [], 0
        for pid in patch_ids:
            paths = band_paths(pid)
            if paths is None:
                missing += 1
                continue
            dn = read_rgb(paths)
            nodata, cloud = quality(dn)
            scored.append({"patch_id": pid, "nodata": nodata, "cloud_like": cloud, "dn": dn})

        after_nodata = [s for s in scored if s["nodata"] <= NODATA_MAX_SHARE]
        kept = [s for s in after_nodata if s["cloud_like"] <= CLOUD_LIKE_MAX_SHARE]

        pool = df[(df.split == official) & df.patch_id.isin([k["patch_id"] for k in kept])]
        pool = pool[pool.type.isin(PER_PATCH)]
        rows_in_pool = len(pool)
        ambiguous = pool.input.map(has_synonym_options)
        pool = pool[~ambiguous]
        examples = []
        for k in kept:
            pid = k["patch_id"]
            render(k["dn"]).save(img_dir / f"{pid}.png")
            rng = random.Random(hashlib.sha256(f"{SEED}-{pid}".encode()).hexdigest())
            mine = pool[pool.patch_id == pid]
            for qtype, n in PER_PATCH.items():
                for row in sample_rows(mine[mine.type == qtype], n, rng):
                    examples.append({
                        "id": int(row.ID), "patch_id": pid, "image": f"images/{pid}.png",
                        "question": row.input, "answer": row.output, "type": row.type,
                        "category": row.category, "split": split,
                        "country": meta.loc[pid, "country"], "season": meta.loc[pid, "season"],
                    })
        rng_out = random.Random(SEED)
        rng_out.shuffle(examples)
        out = WORK / f"{split}.jsonl"
        out.write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in examples) + "\n", encoding="utf-8")

        kept_meta = meta.loc[[k["patch_id"] for k in kept]]
        report["splits"][split] = {
            "patches_in": len(patch_ids),
            "patches_missing_bands": missing,
            "patches_scored": len(scored),
            "dropped_nodata": len(scored) - len(after_nodata),
            "dropped_cloud_like": len(after_nodata) - len(kept),
            "patches_kept": len(kept),
            "annotation_rows_available_for_kept_patches": rows_in_pool,
            "annotation_rows_dropped_fall_autumn_options": int(ambiguous.sum()),
            "examples_written": len(examples),
            "examples_by_type": dict(Counter(e["type"] for e in examples)),
            "examples_by_category": dict(Counter(e["category"] for e in examples)),
            "patches_by_country": kept_meta.country.value_counts().to_dict(),
            "patches_by_season": kept_meta.season.value_counts().to_dict(),
            "distinct_tiles": int(df[df.patch_id.isin(kept_meta.index)].tile.nunique()),
        }
        print(split, json.dumps({k: v for k, v in report["splits"][split].items() if not isinstance(v, dict)}, indent=1))

    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print("report ->", REPORT)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("phase", choices=["select", "extract", "build"])
    args = parser.parse_args()
    sys.exit({"select": cmd_select, "extract": cmd_extract, "build": cmd_build}[args.phase](args) or 0)
