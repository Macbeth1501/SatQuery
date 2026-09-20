"""Zips everything the Kaggle run needs into one upload: the B1 slice, the bench sample and the ml/ code.

    python ml/pack_for_kaggle.py        # writes data/b1_slice/satquery_b1_slice_v0.zip

Upload the zip as a private Kaggle Dataset (you do this; nothing here talks to the network). Its contents
derive from BigEarthNet.txt (CDLA-Permissive-1.0) and BigEarthNet v2.0 imagery; check their terms before
making the dataset public.
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SLICE = ROOT / "data" / "b1_slice"
OUT = SLICE / "satquery_b1_slice_v0.zip"
INCLUDE = ["train.jsonl", "validation.jsonl", "bench.jsonl"]


def main():
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for name in INCLUDE:
            z.write(SLICE / name, f"data/{name}")
        for folder in ("images", "bench_images"):
            for p in sorted((SLICE / folder).glob("*.png")):
                z.write(p, f"data/{folder}/{p.name}")
        for p in sorted((ROOT / "ml").glob("*.py")) + [ROOT / "ml" / "b1_slice_report.json"]:
            z.write(p, f"ml/{p.name}")
    print(f"{OUT}  {OUT.stat().st_size / 2**20:.1f} MiB")


if __name__ == "__main__":
    main()
