"""B1 v2: a training slice, a validation slice and a bench whose questions do not give their answers away.

    python ml/b1_v2.py select        # reserve tiles, rake + sample questions, list the patches needed  (CPU)
    python ml/b1_v2.py extract       # stream the S2 archive once, keeping B02/B03/B04 of those patches   (CPU, ~10 min)
    python ml/b1_v2.py build         # quality rule, PNG renders, train.jsonl / validation.jsonl, gate     (CPU)
    python ml/b1_v2.py bench         # bench_hard.jsonl from the local bench subset, gated                 (CPU)

The first slice (ml/b1_slice.py, data/b1_slice/) is left untouched so run 1 stays reproducible. What changed:

  * Questions are chosen by raking (ml/b5_deleak.py), so the text alone cannot give the answer away. The
    published questions are kept verbatim except "Autumn" -> "Fall" in season options.
  * Questions come first and patches follow them, drawn from ALL 229,114 official train patches, so a rare
    kind of question (a count of 5, an unusual distractor set) is not limited to the patches that happened
    to be extracted. Each patch's other questions are used only if raking chose them.
  * Whole Sentinel tiles are RESERVED: no training or validation patch comes from them, so a bench built on
    those tiles tests generalisation to regions the model never saw. (The B1 finding was that 52 of 54 tiles
    are shared between splits, which is why this has to be decided at selection time.)
  * The same buffer rule as B1: no training patch within BUFFER_CELLS grid cells of a bench or validation patch.

Every rule is a constant below. Counts and gate results go to ml/b1_v2_report.json (committed); data goes to
data/b1_v2/ (not).
"""
import argparse
import glob
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b5_deleak  # noqa: E402
from b1_slice import CLOUD_LIKE_MAX_SHARE, NODATA_MAX_SHARE, RGB_SCALE, BUFFER_CELLS, has_synonym_options  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "BigEarthNet"
PARQUET = DATA / "BigEarthNet.txt" / "BigEarthNet.txt.parquet"
S2_ARCHIVE = DATA / "BigEarthNet-S2" / "BigEarthNet-S2.tar.zst"
BENCH_S2 = DATA / "bench_subset" / "S2"
WORK = ROOT / "data" / "b1_v2"
REPORT = ROOT / "ml" / "b1_v2_report.json"

# ---- the written rules -------------------------------------------------------------------------------
SEED = 20260920
N_RESERVED_TILES = 6  # whole tiles kept out of training and validation, chosen among the bench's busiest tiles
TRAIN_BINARY, TRAIN_MCQ = 10000, 10000  # requested; a category with little weight returns fewer (see sample_by_weight)
VAL_POOL_PATCHES = 8000  # validation patches raked over
VAL_BINARY, VAL_MCQ, VAL_CAPTIONS = 600, 600, 100
TRAIN_CAPTIONS = 1500  # captions kept, from randomly chosen selected patches (the choice questions are the point)
BENCH_BINARY, BENCH_MCQ = 2000, 2000  # requested from the bench pool per part; the yield is what raking leaves
COLS = ["ID", "patch_id", "input", "output", "type", "category", "split", "country", "season"]
# -------------------------------------------------------------------------------------------------------


def load_rows():
    df = pq.read_table(PARQUET, columns=COLS).to_pandas()
    df = df[df.type.isin(["binary", "mcq", "captioning"])]
    return df[~df.input.map(has_synonym_options)]  # same text rule as B1: a Fall/Autumn pair has no answer


def patch_table(df, split):
    p = df[df.split == split].drop_duplicates("patch_id")[["patch_id", "country"]].copy()
    parts = p.patch_id.str.rsplit("_", n=2, expand=True)
    p["scene"], p["row"], p["col"] = parts[0], parts[1].astype(int), parts[2].astype(int)
    p["tile"] = p.scene.str.extract(r"_(T\d\d[A-Z]{3})$")[0]
    return p


def as_examples(df):
    return [{"id": int(i), "patch_id": p, "question": q, "answer": a, "type": t, "category": c, "country": co,
             "season": se} for i, p, q, a, t, c, co, se in zip(df.ID, df.patch_id, df.input, df.output, df.type,
                                                               df.category, df.country, df.season)]


def choose_reserved_tiles(bench):
    """The busiest bench tiles, one per country first, so the held-out test spans regions rather than one place."""
    counts = bench.groupby("tile").size().sort_values(ascending=False)
    country_of = bench.groupby("tile").country.agg(lambda s: s.mode().iloc[0])
    chosen, seen = [], set()
    for tile in counts.index:
        if country_of[tile] not in seen:
            chosen.append(tile)
            seen.add(country_of[tile])
        if len(chosen) == N_RESERVED_TILES:
            break
    for tile in counts.index:  # top up if there were fewer countries than tiles wanted
        if len(chosen) == N_RESERVED_TILES:
            break
        if tile not in chosen:
            chosen.append(tile)
    return chosen, {t: country_of[t] for t in chosen}


def neighbourhood(scene, row, col, k):
    return {(scene, r, c) for r in range(row - k, row + k + 1) for c in range(col - k, col + k + 1)}


def rake_and_sample(df, patches, n_binary, n_mcq, seed):
    """Rakes each (type, category) group over the rows of `patches` and draws its quota. Returns (examples, report).

    Groups are built one at a time so the full pool never sits in memory as dicts."""
    import numpy as _np

    rng = _np.random.default_rng(seed)
    sub = df[df.patch_id.isin(patches) & df.type.isin(["binary", "mcq"])]
    kept, report = [], {}
    for qtype, n_total in (("binary", n_binary), ("mcq", n_mcq)):
        cats = sorted(sub[sub.type == qtype].category.unique())
        for cat in cats:
            group = as_examples(sub[(sub.type == qtype) & (sub.category == cat)])
            group = [b5_deleak.normalise_season(e) for e in group]
            w, worst = b5_deleak.weights_for(group)
            chosen = b5_deleak.sample_by_weight(group, w, n_total // len(cats), rng)
            kept.extend(chosen)
            report[f"{qtype}/{cat}"] = {"in": len(group), "effective_n": round(float(w.sum() ** 2 / (w ** 2).sum())),
                                        "kept": len(chosen), "worst_rate_error_after_raking": round(worst, 4)}
            print(f"  {qtype}/{cat}: {len(group):,} in -> {len(chosen):,} kept (worst rate error {worst:.4f})", flush=True)
    rng.shuffle(kept)
    return kept, report


def cmd_select(_args):
    df = load_rows()
    bench, val_all, train_all = (patch_table(df, s) for s in ("bench", "validation", "train"))
    reserved, reserved_countries = choose_reserved_tiles(bench)
    print("reserved tiles:", reserved_countries, flush=True)
    rng = random.Random(SEED)

    # validation first, because the training buffer is measured from the patches actually chosen for it
    val_pool = val_all[~val_all.tile.isin(reserved)].sample(n=VAL_POOL_PATCHES, random_state=SEED)
    print("validation:", flush=True)
    val, val_report = rake_and_sample(df, set(val_pool.patch_id), VAL_BINARY, VAL_MCQ, SEED)
    val_patches = {e["patch_id"] for e in val}
    val_meta = val_all[val_all.patch_id.isin(val_patches)]

    reference = list(zip(bench.scene, bench.row, bench.col)) + list(zip(val_meta.scene, val_meta.row, val_meta.col))
    blocked = set()
    for s, r, c in reference:
        blocked |= neighbourhood(s, r, c, BUFFER_CELLS)
    in_buffer = np.array([(s, r, c) in blocked for s, r, c in zip(train_all.scene, train_all.row, train_all.col)])
    in_reserved = train_all.tile.isin(reserved).to_numpy()
    eligible = train_all[~in_buffer & ~in_reserved]
    print(f"train patches: {len(train_all):,} official, {int(in_buffer.sum()):,} in the buffer, "
          f"{int((in_reserved & ~in_buffer).sum()):,} more on reserved tiles, {len(eligible):,} eligible", flush=True)
    print("train:", flush=True)
    train, train_report = rake_and_sample(df, set(eligible.patch_id), TRAIN_BINARY, TRAIN_MCQ, SEED)

    train_patches = sorted({e["patch_id"] for e in train})
    caption_patches = set(rng.sample(train_patches, min(TRAIN_CAPTIONS, len(train_patches))))
    caps = df[(df.type == "captioning") & df.patch_id.isin(caption_patches)]
    train += as_examples(caps)
    val_cap_patches = set(rng.sample(sorted(val_patches), min(VAL_CAPTIONS, len(val_patches))))
    val += as_examples(df[(df.type == "captioning") & df.patch_id.isin(val_cap_patches)])

    WORK.mkdir(parents=True, exist_ok=True)
    stats = {"reserved_tiles": reserved_countries, "buffer_cells": BUFFER_CELLS,
             "train_patches_official": len(train_all), "train_patches_in_buffer": int(in_buffer.sum()),
             "train_patches_eligible": len(eligible), "train_patches_needed": len({e["patch_id"] for e in train}),
             "validation_patches_needed": len({e["patch_id"] for e in val}),
             "train_rake_report": train_report, "validation_rake_report": val_report}
    (WORK / "selection.json").write_text(json.dumps({"train": train, "validation": val, "stats": stats},
                                                    ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in stats.items() if not k.endswith("report")}, indent=1))
    print(f"train examples {len(train):,} ({Counter(e['type'] for e in train)}), validation {len(val):,}")


def cmd_extract(_args):
    """One streaming pass over the S2 archive; keeps only B02/B03/B04 of the selected patches."""
    sel = json.loads((WORK / "selection.json").read_text(encoding="utf-8"))
    wanted = {e["patch_id"] for e in sel["train"]} | {e["patch_id"] for e in sel["validation"]}
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
                if Path(member.name).parent.name in wanted:
                    tar.extract(member, dest)
                    kept += 1
    print(f"done: scanned {scanned:,} members, kept {kept:,} files for {len(wanted):,} patches", flush=True)


def read_rgb(paths):
    chans = []
    for band in ("B04", "B03", "B02"):
        with rasterio.open(paths[band]) as src:
            chans.append(src.read(1))
    return np.stack(chans, -1)


def render(dn):
    return Image.fromarray((np.clip(dn.astype("float32") / RGB_SCALE, 0, 1) * 255).astype(np.uint8))


def quality(dn):
    return float(np.mean((dn == 0).all(axis=-1))), float(np.mean(dn.astype("float32").mean(axis=-1) >= 2500))


def cmd_build(_args):
    sel = json.loads((WORK / "selection.json").read_text(encoding="utf-8"))
    index = {p.stem: p for p in (WORK / "raw_s2").rglob("*.tif")}
    (WORK / "images").mkdir(exist_ok=True)
    report = {"rules": {"seed": SEED, "buffer_cells": BUFFER_CELLS, "nodata_max_share": NODATA_MAX_SHARE,
                        "cloud_like_max_share": CLOUD_LIKE_MAX_SHARE, "rgb_scale": RGB_SCALE,
                        "method": "ml/b5_deleak.py raking; published questions kept verbatim except Autumn -> Fall"},
              "select": sel["stats"], "splits": {}}
    for split in ("train", "validation"):
        examples = sel[split]
        patches = sorted({e["patch_id"] for e in examples})
        good, missing, bad = set(), 0, 0
        for pid in patches:
            paths = {b: index.get(f"{pid}_{b}") for b in ("B02", "B03", "B04")}
            if not all(paths.values()):
                missing += 1
                continue
            dn = read_rgb(paths)
            nodata, cloud = quality(dn)
            if nodata > NODATA_MAX_SHARE or cloud > CLOUD_LIKE_MAX_SHARE:
                bad += 1
                continue
            render(dn).save(WORK / "images" / f"{pid}.png")
            good.add(pid)
        out = []
        for e in examples:
            if e["patch_id"] in good:
                out.append({**e, "image": f"images/{e['patch_id']}.png", "split": split})
        random.Random(SEED).shuffle(out)
        (WORK / f"{split}.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in out) + "\n",
                                             encoding="utf-8")
        choice = [e for e in out if e["type"] in ("binary", "mcq")]
        report["splits"][split] = {
            "patches_selected": len(patches), "patches_missing_bands": missing, "patches_dropped_quality": bad,
            "patches_kept": len(good), "examples_written": len(out),
            "examples_by_type": dict(Counter(e["type"] for e in out)),
            "examples_by_category": dict(Counter(f"{e['type']}/{e['category']}" for e in out)),
        }
        if split == "train":
            passed, summary = b5_deleak.gate(choice)
            report["splits"][split]["text_only_gate"] = {"passed": passed, "tolerance": 0.03, **summary}
            print("TRAIN GATE passed:", passed, json.dumps(summary["by_type"]))
        print(split, {k: v for k, v in report["splits"][split].items() if not isinstance(v, dict)})
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print("report ->", REPORT)


def cmd_bench(_args):
    """bench_hard.jsonl: the local bench subset, raked, split into `main` and `heldout` (reserved tiles)."""
    import b5_text_only as T

    sel = json.loads((WORK / "selection.json").read_text(encoding="utf-8"))
    reserved = set(sel["stats"]["reserved_tiles"])
    df = load_rows()
    bench_df = df[df.split == "bench"]
    table = patch_table(df, "bench").set_index("patch_id")
    (WORK / "bench_images").mkdir(exist_ok=True)
    report = {"reserved_tiles": sorted(reserved), "parts": {}}
    examples = []
    for part in ("main", "heldout"):
        ids = set(table.index[table.tile.isin(reserved) == (part == "heldout")])
        print(part, len(ids), "patches", flush=True)
        kept, rep = rake_and_sample(bench_df, ids, BENCH_BINARY, BENCH_MCQ, SEED)
        examples += [{**e, "part": part} for e in kept]
        report["parts"][part] = {"patches": len(ids), "rake": rep,
                                 "examples_by_type": dict(Counter(e["type"] for e in kept))}
    partners = sorted({e["patch_id"] for e in examples})
    prng = random.Random(SEED)
    for e in examples:  # matched/mismatched: the same question against a different patch's picture
        other = prng.choice(partners)
        while other == e["patch_id"]:
            other = prng.choice(partners)
        e["pair_patch_id"] = other
    for pid in sorted({e["patch_id"] for e in examples} | {e["pair_patch_id"] for e in examples}):
        target = WORK / "bench_images" / f"{pid}.png"
        if not target.exists():
            paths = {b: Path(glob.glob(str(BENCH_S2 / "**" / f"{pid}_{b}.tif"), recursive=True)[0])
                     for b in ("B02", "B03", "B04")}
            render(read_rgb(paths)).save(target)
    for e in examples:
        e["image"] = f"bench_images/{e['patch_id']}.png"
        e["pair_image"] = f"bench_images/{e['pair_patch_id']}.png"
    random.Random(SEED).shuffle(examples)
    (WORK / "bench_hard.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in examples) + "\n",
                                           encoding="utf-8")

    # The claim being tested: a text-only model, fitted on either training set, scores at chance on bench_hard.
    fits = {"leaky_run1_slice": T.load_jsonl(ROOT / "data" / "b1_slice" / "train.jsonl"),
            "deleaked_v2_slice": T.load_jsonl(WORK / "train.jsonl") if (WORK / "train.jsonl").exists() else None}
    gates = {}
    for name, train in fits.items():
        if train is None:
            continue
        gates[name] = {}
        for part in ("main", "heldout"):
            _, summary = T.score(train, [e for e in examples if e["part"] == part])
            gates[name][part] = summary["by_type"]
    report["text_only_on_bench_hard"] = gates
    (ROOT / "ml" / "b1_v2_bench_report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False),
                                                         encoding="utf-8")
    print(json.dumps(gates, indent=1))
    print(f"bench_hard: {len(examples)} examples ->", WORK / "bench_hard.jsonl")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("phase", choices=["select", "extract", "build", "bench"])
    args = parser.parse_args()
    sys.exit({"select": cmd_select, "extract": cmd_extract, "build": cmd_build, "bench": cmd_bench}[args.phase](args) or 0)
