"""Free-form descriptions from the run-2 adapter and from the base model (adapter off), on the live-demo samples.

    .venv-ml/Scripts/python.exe ml/b5_freeform_compare.py --out data/b5_eval/freeform_compare.json

For each real BigEarthNet patch in frontend/src/data/realSamples.json, asks the same free-form prompts twice
through `serve_vqa.Engine`, once with the adapter and once with it disabled, and stores both replies beside the
patch's known facts (country, season, and its reference yes/no and a-d answers). It does not grade: the replies
are read by hand. Five patches are a spot check, not an evaluation.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

PROMPTS = ("Describe the image", "Describe the scenery", "What land cover is visible in this image?")
COUNTRIES = ("ireland", "lithuania", "serbia", "portugal", "finland", "austria", "belgium", "switzerland",
             "latvia", "estonia", "kosovo")
SEASONS = ("spring", "summer", "fall", "autumn", "winter")


def stated(reply, words):
    """The words from `words` that the reply names, in order of first mention."""
    low = reply.lower()
    return sorted({w for w in words if w in low}, key=low.index)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--adapter", default=str(ROOT / "data" / "b5_run2" / "adapter_final"))
    ap.add_argument("--out", default=str(ROOT / "data" / "b5_eval" / "freeform_compare.json"))
    args = ap.parse_args()
    os.environ.setdefault("HF_HOME", str(ROOT / "data" / "hf_cache"))
    os.environ.setdefault("HF_HUB_OFFLINE", "1")

    from serve_vqa import Engine, question_kind

    assert all(question_kind(p) == "free" for p in PROMPTS)
    samples = json.loads((ROOT / "frontend" / "src" / "data" / "realSamples.json").read_text(encoding="utf-8"))
    engine = Engine(args.adapter, 448)
    rows = []
    for sample in samples["samples"]:
        image = ROOT / "frontend" / "public" / "real" / sample["rasterFile"]
        facts = {"country": sample["country"], "season": sample["season"], "acquired": sample["acquired"],
                 "reference": [(q["question"], q["answer"]) for q in sample["questions"]]}
        for prompt in PROMPTS:
            for who in ("adapter", "base"):
                t = time.perf_counter()
                result = engine.answer(image, prompt, free_form=who)
                assert result["answered_by"] == who
                reply = result["answer_text"]
                rows.append({"sample": sample["id"], "prompt": prompt, "model": who, "reply": reply,
                             "countries_named": stated(reply, COUNTRIES), "seasons_named": stated(reply, SEASONS),
                             "facts": facts, "seconds": round(time.perf_counter() - t, 1)})
                print(f"[{sample['id']} | {who:7} | {prompt}] {reply}", flush=True)

    summary = {}
    for who in ("adapter", "base"):
        mine = [r for r in rows if r["model"] == who]
        summary[who] = {
            "replies": len(mine),
            "name_a_country": sum(bool(r["countries_named"]) for r in mine),
            "name_a_wrong_country": sum(any(c != r["facts"]["country"].lower() for c in r["countries_named"])
                                        for r in mine),
            "name_a_season": sum(bool(r["seasons_named"]) for r in mine),
            "name_a_wrong_season": sum(any(s.replace("autumn", "fall") != r["facts"]["season"].lower()
                                           for s in r["seasons_named"]) for r in mine),
        }
    Path(args.out).write_text(json.dumps({"prompts": PROMPTS, "summary": summary, "rows": rows}, indent=2),
                              encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
