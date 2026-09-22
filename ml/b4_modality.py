"""B4 / M9: fit the optical-vs-SAR pixel classifier and score it on held-out tiles (ML_PLAN phase 0).

    .venv-ml/Scripts/python.exe ml/b4_modality.py fit --train 4000 --test 2000

Reads the B1 pool (data/b1_full, built by ml/b1_full.py), takes Sentinel-2 as optical and Sentinel-1 as SAR, and
splits by BigEarthNet's official `split` column: `train` patches fit the model, `test` patches score it, and no
patch appears in both.

The point is NOT to tell a raw S2 uint16 patch from a raw S1 float32 one; the dtype alone would do that, and the
metadata service already decides those from tags and file names. The model is for files that arrive with neither,
which in practice are renderings, so every patch is presented in five of them and the features are
dtype-independent (backend/app/services/modality_model.py):

    native     S2 four bands uint16 DN / S1 two bands float dB, as stored
    rgb8       S2 true colour 8-bit / S1 false colour (VV, VH, VV-VH) 8-bit
    gray8      one 8-bit band: S2 RGB mean / S1 VV
    gray_rep3  that same grey band repeated three times, as a PNG export gives
    linear     float: S2 reflectance (DN/10000) / S1 linear power (from dB)

Baseline: what the metadata service does today for a file with no tag and no name hint — it answers "optical"
every time, so it is right on exactly the optical half. The model has to beat that on held-out tiles, per
rendering, or it is not wired in. Output: backend/app/services/modality_model.json (coefficients, standardisation
and the held-out scores) and ml/b4_modality_report.json.
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.services.modality_model import FEATURE_NAMES, MODEL_PATH, features  # noqa: E402

POOL = ROOT / "data" / "b1_full"
PARQUET = ROOT / "data" / "BigEarthNet" / "BigEarthNet.txt" / "BigEarthNet.txt.parquet"
SHAPES = {"s2": (4, 120, 120), "s1": (2, 120, 120)}
DTYPES = {"s2": np.uint16, "s1": np.float16}
RENDERINGS = ("native", "rgb8", "gray8", "gray_rep3", "linear")
# S1 dB range used to make an 8-bit render; the usual display stretch for Sentinel-1 GRD backscatter.
S1_DB_RANGE = (-25.0, 0.0)
READ_MAP_BYTES = 1 << 40
S2_RGB_SCALE = 3000.0  # the DN that maps to white in ml/b1_slice.py's render, kept identical here


def to_uint8(x, lo, hi):
    return (np.clip((x.astype(np.float32) - lo) / (hi - lo), 0, 1) * 255).astype(np.uint8)


def render(patch, modality, how):
    """One stored patch (bands, 120, 120) as it might arrive from a user."""
    if how == "native":
        return patch
    if modality == "s2":
        rgb = patch[[0, 1, 2]].astype(np.float32)  # stored B04, B03, B02 = R, G, B
        if how == "linear":
            return patch.astype(np.float32) / 10000.0
        rgb8 = to_uint8(rgb, 0.0, S2_RGB_SCALE)
    else:
        db = patch.astype(np.float32)
        if how == "linear":
            return np.power(10.0, db / 10.0).astype(np.float32)
        vv, vh = db[0], db[1]
        rgb8 = to_uint8(np.stack([vv, vh, vv - vh]), *S1_DB_RANGE)
    if how == "rgb8":
        return rgb8
    grey = rgb8.mean(axis=0).astype(np.uint8)[None] if modality == "s2" else rgb8[[0]]
    return np.repeat(grey, 3, axis=0) if how == "gray_rep3" else grey


def splits():
    """patch_id -> official split, for the patches that have one."""
    import pyarrow.parquet as pq

    table = pq.read_table(PARQUET, columns=["patch_id", "split"]).to_pandas().drop_duplicates("patch_id")
    return dict(zip(table.patch_id, table.split))


def sample(modality, wanted_split, split_of, limit, rng):
    """Up to `limit` stored patches of one modality whose official split is `wanted_split`."""
    import lmdb

    # A big read map: the ingest process grows the store's map as it runs, and a reader opened with a smaller
    # one fails with MDB_PAGE_NOTFOUND once the writer passes it.
    env = lmdb.open(str(POOL / modality), readonly=True, lock=False, readahead=False, map_size=READ_MAP_BYTES)
    out = []
    with env.begin() as txn:
        keys = [k for k, _ in txn.cursor() if split_of.get(k.decode()) == wanted_split]
        rng.shuffle(keys)
        for key in keys[:limit]:
            out.append(np.frombuffer(txn.get(key), DTYPES[modality]).reshape(SHAPES[modality]))
    env.close()
    return out


def rows(patches, modality, label):
    for patch in patches:
        for how in RENDERINGS:
            yield {"x": features(render(patch, modality, how)), "y": label, "rendering": how}


def cmd_fit(args):
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    rng = random.Random(0)
    split_of = splits()
    data = {}
    for part, wanted, n in (("train", "train", args.train), ("test", "test", args.test)):
        optical = sample("s2", wanted, split_of, n // 2, rng)
        sar = sample("s1", wanted, split_of, n // 2, rng)
        print(f"{part}: {len(optical)} optical, {len(sar)} SAR patches", flush=True)
        data[part] = list(rows(optical, "s2", 0)) + list(rows(sar, "s1", 1))
    if not data["train"] or not data["test"]:
        sys.exit("no patches found: is data/b1_full built, and does it cover both splits yet?")

    X = np.stack([r["x"] for r in data["train"]])
    y = np.array([r["y"] for r in data["train"]])
    scaler = StandardScaler().fit(X)
    model = LogisticRegression(max_iter=2000, C=1.0).fit(scaler.transform(X), y)

    Xt = np.stack([r["x"] for r in data["test"]])
    yt = np.array([r["y"] for r in data["test"]])
    predicted = model.predict(scaler.transform(Xt))
    # What a served call costs: feature extraction over one image (the regression itself is a dot product).
    timed = sample("s2", "test", split_of, 40, random.Random(1)) or []
    start = time.perf_counter()
    for patch in timed:
        features(render(patch, "s2", "rgb8"))
    per_call_ms = (time.perf_counter() - start) * 1000.0 / max(len(timed), 1)
    evaluation = {"overall": {"n": len(yt), "accuracy": float((predicted == yt).mean()),
                              "baseline_always_optical": float((yt == 0).mean())}}
    for how in RENDERINGS:
        mask = np.array([r["rendering"] == how for r in data["test"]])
        evaluation[how] = {"n": int(mask.sum()), "accuracy": float((predicted[mask] == yt[mask]).mean()),
                           "sar_recall": float((predicted[mask & (yt == 1)] == 1).mean()),
                           "optical_recall": float((predicted[mask & (yt == 0)] == 0).mean())}

    out = {
        "feature_names": list(FEATURE_NAMES),
        "classes": {"0": "optical", "1": "sar"},
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "coef": model.coef_[0].tolist(),
        "intercept": float(model.intercept_[0]),
        "fitted_on": {"pool": "data/b1_full (BigEarthNet S2 = optical, S1 = SAR)", "split": "official",
                      "train_patches": args.train, "test_patches": args.test, "renderings": list(RENDERINGS)},
        "evaluation": evaluation,
        "note": ("Fitted on Sentinel-1/2 only; Cartosat/RISAT textures are outside its training. The baseline is "
                 "what metadata_service does for a file with no tag and no name hint: always 'optical'."),
        "fitted_at": time.strftime("%Y-%m-%d %H:%M"),
    }
    MODEL_PATH.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    report = {**out, "feature_ms_per_call_on_test": round(per_call_ms, 3)}
    (Path(__file__).resolve().parent / "b4_modality_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evaluation, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fit")
    f.add_argument("--train", type=int, default=4000, help="patches (half optical, half SAR) for fitting")
    f.add_argument("--test", type=int, default=2000, help="held-out patches from the official test split")
    f.set_defaults(func=cmd_fit)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
