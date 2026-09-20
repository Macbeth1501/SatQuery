"""Does Qwen2-VL-2B-Instruct run 4-bit on this machine, and at what input resolution?

Measurement only. Nothing here touches the backend or the dummy specialists (Development Plan
section 2.5); it exists to replace the log's unverified claim that 4-bit inference fits a 4 GB card
at capped resolution with numbers. Run it from the repo root with the ML venv:

    HF_HOME=D:/Projects/SatQuery/data/hf_cache .venv-ml/Scripts/python.exe tools/ml_smoke_test.py

For one BigEarthNet.txt bench patch it renders a Sentinel-2 RGB image (B04/B03/B02) and a Sentinel-1
VV image, then generates from the model with one image and with two, at several square input sizes.
For each run it records peak GPU memory, wall time and the model's output, and it records an
out-of-memory failure as a result rather than crashing. Results go to
data/ml_smoke/results.json (gitignored).

One patch is a smoke test, not an evaluation: the outputs show the model runs and what it says, and
say nothing about accuracy.
"""
import glob
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import rasterio
import torch
from PIL import Image
from transformers import AutoProcessor, BitsAndBytesConfig, Qwen2VLForConditionalGeneration

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "data" / "BigEarthNet" / "bench_subset"
PARQUET = ROOT / "data" / "BigEarthNet" / "BigEarthNet.txt" / "BigEarthNet.txt.parquet"
OUT = ROOT / "data" / "ml_smoke"

MODEL_ID = "Qwen/Qwen2-VL-2B-Instruct"
REVISION = "895c3a49bc3fa70a340399125c650a463535e71c"  # read from the Hub on 2026-09-20, then downloaded
SIZES = [224, 448, 672, 896]  # square inputs, multiples of 28 (14 px patch x 2x2 merge)
MAX_NEW_TOKENS = 96


def find_patch():
    """First bench patch that has a caption row, plus its captioning prompt and reference answer."""
    cols = ["patch_id", "s1_name", "input", "output", "type", "split"]
    rows = pq.read_table(PARQUET, columns=cols).to_pandas()
    bench = rows[(rows.split == "bench") & (rows.type == "captioning")]
    for _, row in bench.iterrows():
        s2 = glob.glob(str(BENCH / "S2" / "**" / f"{row.patch_id}_B04.tif"), recursive=True)
        s1 = glob.glob(str(BENCH / "S1" / "**" / f"{row.s1_name}_VV.tif"), recursive=True)
        if s2 and s1:
            return row, Path(s2[0]).parent, Path(s1[0]).parent
    raise SystemExit("no bench patch with both S1 and S2 files found")


def stretch(arr, lo=2, hi=98):
    a, b = np.percentile(arr, [lo, hi])
    return np.clip((arr - a) / max(b - a, 1e-9), 0, 1)


def read(path):
    with rasterio.open(path) as src:
        return src.read(1).astype("float32")


def render_s2(s2_dir, patch_id):
    bands = [stretch(read(s2_dir / f"{patch_id}_{b}.tif")) for b in ("B04", "B03", "B02")]
    return Image.fromarray((np.stack(bands, -1) * 255).astype(np.uint8))


def render_s1(s1_dir, s1_name):
    vv = stretch(read(s1_dir / f"{s1_name}_VV.tif"))
    return Image.fromarray((vv * 255).astype(np.uint8)).convert("RGB")


def run(model, processor, images, prompt, size):
    resized = [im.resize((size, size), Image.BICUBIC) for im in images]
    content = [{"type": "image", "image": im} for im in resized] + [{"type": "text", "text": prompt}]
    text = processor.apply_chat_template(
        [{"role": "user", "content": content}], tokenize=False, add_generation_prompt=True
    )
    inputs = processor(text=[text], images=resized, return_tensors="pt").to("cuda")
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    start = time.time()
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)
    torch.cuda.synchronize()
    seconds = time.time() - start
    new = out[:, inputs["input_ids"].shape[1]:]
    return {
        "input_tokens": int(inputs["input_ids"].shape[1]),
        "new_tokens": int(new.shape[1]),
        "seconds": round(seconds, 2),
        "peak_allocated_mib": round(torch.cuda.max_memory_allocated() / 2**20),
        "output": processor.batch_decode(new, skip_special_tokens=True)[0],
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    row, s2_dir, s1_dir = find_patch()
    s2_img, s1_img = render_s2(s2_dir, row.patch_id), render_s1(s1_dir, row.s1_name)
    s2_img.resize((448, 448)).save(OUT / "sample_s2_rgb.png")
    s1_img.resize((448, 448)).save(OUT / "sample_s1_vv.png")

    free0, total = torch.cuda.mem_get_info()
    print(f"GPU {torch.cuda.get_device_name(0)}: {total / 2**20:.0f} MiB total, "
          f"{free0 / 2**20:.0f} MiB free before load (the desktop already holds the rest)", flush=True)

    quant = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
    )
    started = time.time()
    model = Qwen2VLForConditionalGeneration.from_pretrained(
        MODEL_ID, revision=REVISION, quantization_config=quant, device_map={"": 0}, dtype=torch.bfloat16
    )
    processor = AutoProcessor.from_pretrained(MODEL_ID, revision=REVISION)
    torch.cuda.synchronize()
    free1, _ = torch.cuda.mem_get_info()
    loaded = {
        "load_seconds": round(time.time() - started, 1),
        "weights_allocated_mib": round(torch.cuda.memory_allocated() / 2**20),
        "free_after_load_mib": round(free1 / 2**20),
    }
    print("loaded:", loaded, flush=True)

    prompt = row.input
    results = {
        "model": MODEL_ID, "revision": REVISION, "torch": torch.__version__,
        "patch_id": row.patch_id, "prompt": prompt, "reference": row.output,
        "loaded": loaded, "runs": [],
    }
    for n_images, images in ((1, [s2_img]), (2, [s2_img, s1_img])):
        for size in SIZES:
            entry = {"images": n_images, "size": size}
            try:
                entry.update(run(model, processor, images, prompt, size))
            except torch.cuda.OutOfMemoryError:
                entry["error"] = "CUDA out of memory"
                torch.cuda.empty_cache()
            except Exception as exc:  # record, then keep sweeping
                entry["error"] = f"{type(exc).__name__}: {str(exc)[:200]}"
                torch.cuda.empty_cache()
            results["runs"].append(entry)
            print({k: v for k, v in entry.items() if k != "output"}, flush=True)
            (OUT / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
