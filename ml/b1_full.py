"""B1 (full): stream the BigEarthNet S2 and S1 archives into LMDB, never unpacking them to disk (ML_PLAN phase 1).

    .venv-ml/Scripts/python.exe ml/b1_full.py measure --modality s2 --limit 10000
    .venv-ml/Scripts/python.exe ml/b1_full.py measure --modality s1 --limit 10000

`measure` is the step the plan asks for before the full run: it ingests the first N complete patches of one
archive into a scratch LMDB under data/b1_full_measure/ and writes ml/b1_full_measure_<modality>.json with the
bytes per patch actually used, the read rate, and a projection to the whole archive. The projection assumes the
first N patches are typical of the rest (same shape, same compression ratio); it is labelled as a projection.

What is stored, per patch, as raw little-endian array bytes (shape and dtype are fixed, so no header):
  * S2: B04, B03, B02, B08 (red, green, blue, NIR, all 10 m) as uint16 DN, 4 x 120 x 120;
  * S1: VV, VH as float16 (the archive holds float32 backscatter in dB; float16 keeps about 3 significant
    digits, far finer than speckle), 2 x 120 x 120.
Both are keyed by the S2 patch id. S1 folders are named by `s1_name`; BigEarthNet.txt.parquet carries both
columns, so the join needs no other metadata file. An S1 patch with no parquet row is stored under its own
name with an `s1:` prefix and counted, never dropped silently.

Still to do for the full run (phase 1, not needed to measure): the official split with the 2-cell buffer, the
5%-cloud cap and its pairs_in/pairs_kept report, and the box rows.

On Windows an LMDB data file is as large as its map size from the start, so the map begins small and doubles
when full. Resumable: a patch whose key is already present is skipped before it is decoded.
"""
import argparse
import json
import sys
import tarfile
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "BigEarthNet"
PARQUET = DATA / "BigEarthNet.txt" / "BigEarthNet.txt.parquet"
ARCHIVES = {
    "s2": DATA / "BigEarthNet-S2" / "BigEarthNet-S2.tar.zst",
    "s1": DATA / "BigEarthNet-S1" / "BigEarthNet-S1.tar.zst",
}
BANDS = {"s2": ("B04", "B03", "B02", "B08"), "s1": ("VV", "VH")}
DTYPES = {"s2": np.uint16, "s1": np.float16}
SIZE = 120
MEASURE_DIR = ROOT / "data" / "b1_full_measure"
COMMIT_EVERY = 500
INITIAL_MAP_BYTES = 1 << 30


def band_of(name, modality):
    """'B04' for '..._26_57_B04.tif', or None when the file is not a band we keep."""
    if not name.endswith(".tif"):
        return None
    band = name[:-4].rsplit("_", 1)[-1]
    return band if band in BANDS[modality] else None


def decode(blobs, modality):
    """Band tif bytes -> one C-contiguous array, bands first, in BANDS order."""
    from rasterio.io import MemoryFile

    chans = []
    for band in BANDS[modality]:
        with MemoryFile(blobs[band]) as mem, mem.open() as src:
            arr = src.read(1)
        if arr.shape != (SIZE, SIZE):
            raise ValueError(f"band {band} has shape {arr.shape}, expected {(SIZE, SIZE)}")
        chans.append(arr)
    return np.ascontiguousarray(np.stack(chans).astype(DTYPES[modality]))


def s1_to_patch():
    import pyarrow.parquet as pq

    table = pq.read_table(PARQUET, columns=["s1_name", "patch_id"]).to_pandas().drop_duplicates("s1_name")
    return dict(zip(table.s1_name, table.patch_id))


def patches(archive, modality):
    """Yields (folder name, {band: tif bytes}) once every kept band of a folder has been read, plus the
    compressed bytes consumed so far. Bands of one folder need not be adjacent in the archive."""
    import zstandard

    need = set(BANDS[modality])
    pending = {}
    with archive.open("rb") as fh:
        reader = zstandard.ZstdDecompressor().stream_reader(fh)
        with tarfile.open(fileobj=reader, mode="r|") as tar:
            for member in tar:
                if not member.isfile():
                    continue
                band = band_of(member.name, modality)
                if band is None:
                    continue
                folder = Path(member.name).parent.name
                got = pending.setdefault(folder, {})
                got[band] = tar.extractfile(member).read()
                if need <= got.keys():
                    yield folder, pending.pop(folder), fh.tell()


class Store:
    """An LMDB environment whose map doubles when full (the file is the map size on Windows)."""

    def __init__(self, path):
        import lmdb

        self.lmdb = lmdb
        path.mkdir(parents=True, exist_ok=True)
        self.env = lmdb.open(str(path), map_size=INITIAL_MAP_BYTES, subdir=True, lock=True, readahead=False)
        self.batch = {}

    def has(self, key):
        if key in self.batch:
            return True
        with self.env.begin() as txn:
            return txn.get(key) is not None

    def put(self, key, value):
        self.batch[key] = value
        if len(self.batch) >= COMMIT_EVERY:
            self.commit()

    def commit(self):
        while self.batch:
            try:
                with self.env.begin(write=True) as txn:
                    for key, value in self.batch.items():
                        txn.put(key, value)
                self.batch = {}
            except self.lmdb.MapFullError:
                self.env.set_mapsize(self.env.info()["map_size"] * 2)

    def used_bytes(self):
        return (self.env.info()["last_pgno"] + 1) * self.env.stat()["psize"]

    def close(self):
        self.commit()
        self.env.close()


def cmd_measure(args):
    modality, archive = args.modality, ARCHIVES[args.modality]
    mapping = s1_to_patch() if modality == "s1" else None
    store = Store(MEASURE_DIR / modality)
    stored = skipped = unmatched = 0
    value_bytes = 0
    start = time.perf_counter()
    compressed = 0
    for folder, blobs, compressed in patches(archive, modality):
        key = folder if mapping is None else mapping.get(folder)
        if key is None:
            key, unmatched = f"s1:{folder}", unmatched + 1
        key = key.encode()
        if store.has(key):
            skipped += 1
        else:
            value = decode(blobs, modality).tobytes()
            store.put(key, value)
            value_bytes += len(value)
            stored += 1
        if (stored + skipped) % 1000 == 0:
            print(f"{modality}: {stored + skipped:,} patches, {time.perf_counter() - start:.0f} s", flush=True)
        if stored + skipped >= args.limit:
            break
    store.commit()
    seconds = time.perf_counter() - start
    used = store.used_bytes()
    store.close()

    n = stored + skipped
    archive_bytes = archive.stat().st_size
    fraction = compressed / archive_bytes if archive_bytes else 0.0
    projected_patches = round(n / fraction) if fraction else None
    per_patch = used / n if n else None
    report = {
        "modality": modality,
        "archive": str(archive.relative_to(ROOT)),
        "archive_bytes": archive_bytes,
        "bands": list(BANDS[modality]),
        "dtype": np.dtype(DTYPES[modality]).name,
        "patches_measured": n,
        "stored_this_run": stored,
        "skipped_already_present": skipped,
        "s1_without_parquet_row": unmatched if modality == "s1" else None,
        "array_bytes_per_patch": value_bytes / stored if stored else None,
        "lmdb_used_bytes": used,
        "lmdb_bytes_per_patch": per_patch,
        "compressed_bytes_read": compressed,
        "archive_fraction_read": fraction,
        "seconds_this_run": round(seconds, 1),
        "patches_per_second_this_run": round(stored / seconds, 1) if seconds and stored else None,
        "projection_note": "assumes the first patches are typical of the whole archive; not a measurement",
        "projected_patches_in_archive": projected_patches,
        "projected_lmdb_gib": round(per_patch * projected_patches / 2**30, 1) if per_patch and projected_patches
        else None,
        "projected_hours_single_process": round(seconds / fraction / 3600, 1) if fraction and stored == n
        else None,
        "measured_on": time.strftime("%Y-%m-%d"),
    }
    out = Path(__file__).resolve().parent / f"b1_full_measure_{modality}.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("measure", help="ingest the first N patches of one archive and project the full size")
    m.add_argument("--modality", choices=sorted(ARCHIVES), required=True)
    m.add_argument("--limit", type=int, default=10000)
    m.set_defaults(func=cmd_measure)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
