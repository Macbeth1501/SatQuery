"""Stream BigEarthNet .tar.zst archives and keep only the BigEarthNet.txt `bench` patches.

The full archives are ~117 GB compressed and will not fit uncompressed beside an LMDB copy, so
nothing is unpacked wholesale: each archive is read once as a stream and only members whose path
contains a bench patch name are written out.

    python tools/extract_bigearthnet_bench.py
"""
import sys
import tarfile
import time
from pathlib import Path

import pyarrow.parquet as pq
import zstandard

ROOT = Path(__file__).resolve().parents[1] / "data" / "BigEarthNet"
PARQUET = ROOT / "BigEarthNet.txt" / "BigEarthNet.txt.parquet"
OUT = ROOT / "bench_subset"


def bench_names():
    table = pq.read_table(PARQUET, columns=["patch_id", "s1_name", "split"]).to_pandas()
    bench = table[table.split == "bench"]
    return set(bench.patch_id), set(bench.s1_name)


def extract(archive: Path, wanted: set, dest: Path) -> tuple:
    dest.mkdir(parents=True, exist_ok=True)
    kept = scanned = 0
    started = time.time()
    with archive.open("rb") as fh:
        reader = zstandard.ZstdDecompressor().stream_reader(fh)
        with tarfile.open(fileobj=reader, mode="r|") as tar:
            for member in tar:
                scanned += 1
                if scanned % 200000 == 0:
                    print(f"  {archive.name}: scanned {scanned:,}, kept {kept:,}, "
                          f"{time.time() - started:,.0f}s", flush=True)
                if not member.isfile():
                    continue
                parts = Path(member.name).parts
                if not any(p in wanted for p in parts):
                    continue
                tar.extract(member, dest)
                kept += 1
    return scanned, kept


if __name__ == "__main__":
    s2_names, s1_names = bench_names()
    print(f"bench: {len(s2_names)} S2 patches, {len(s1_names)} S1 patches", flush=True)
    for label, names in (("S2", s2_names), ("S1", s1_names)):
        archive = ROOT / f"BigEarthNet-{label}" / f"BigEarthNet-{label}.tar.zst"
        scanned, kept = extract(archive, names, OUT / label)
        print(f"{label}: scanned {scanned:,} members, kept {kept:,} files", flush=True)
