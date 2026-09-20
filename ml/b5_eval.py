"""B5 evaluation on the BigEarthNet.txt `bench` split (1,082 manually verified patches).

    python ml/b5_eval.py prepare                                  # build the bench sample once
    python ml/b5_eval.py run --out data/b5_eval/base.json         # untuned base model (--data DIR to relocate)
    python ml/b5_eval.py run --adapter data/b5_run/adapter_final --out data/b5_eval/tuned.json
    python ml/b5_eval.py run --adapter data/b5_run/adapter_final --blank-image --out data/b5_eval/tuned_blind.json
    python ml/b5_eval.py run --data data/b1_v2 --bench-file bench_hard.jsonl --adapter ... --out ...   # leak-free bench

The same fixed sample and the same scoring rules (b5_common.score_choice / caption_mentions) are used for
the base model and the adapter, so the difference between the two files is the effect of training.

What the numbers can and cannot say:
  * READ `acc_among_readable` NEXT TO `acc`. The untuned base model mostly answers in sentences, so its plain
    accuracy (below chance) measures format compliance, not vision. A tuned adapter will fix the format and
    gain a lot from that alone; only the readable-only figure and the per-category numbers say whether it
    learned anything about the images.
  * binary and multiple-choice accuracy are exact matches against the reference letter or yes/no. Chance is
    50% for binary and 25% for four options, and the answers are balanced, so a model that ignores the image
    cannot beat chance by much. "Unreadable" replies (no yes/no or a-d found) count as wrong and are reported.
  * captions are NOT scored for quality. We only report whether the caption names the right country and
    season, because those two facts are checkable and an image can support them. It is not a caption metric.
  * bench patches share Sentinel tiles with the training pool (see ml/b1_slice.py), so accuracy here is
    optimistic for regions the model has never seen. Read the base-versus-tuned difference, not the level.
"""
import argparse
import glob
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from b5_common import caption_mentions, generate, load_jsonl, load_model, normalise_choice, score_choice  # noqa: E402

# `prepare` needs the raw BigEarthNet files and so only runs on the machine that has them; b1_slice (which
# pulls in rasterio and zstandard) is therefore imported there, not at module level. `run` needs only the
# packed sample, which is why it works unchanged on Kaggle.
DEFAULT_DATA = Path(__file__).resolve().parents[1] / "data" / "b1_slice"
SEED = 20260920
N_BINARY, N_MCQ, N_CAPTION = 400, 400, 60  # sample sizes drawn from the 6,927 / 5,550 / 970 bench rows


def prepare(out_dir):
    import pyarrow.parquet as pq

    from b1_slice import PARQUET, ROOT, has_synonym_options, read_rgb, render

    OUT = Path(out_dir)
    BENCH_S2 = ROOT / "data" / "BigEarthNet" / "bench_subset" / "S2"
    cols = ["ID", "patch_id", "input", "output", "type", "category", "country", "season", "split"]
    df = pq.read_table(PARQUET, columns=cols).to_pandas()
    bench = df[df.split == "bench"]
    n_synonym = int(bench.input.map(has_synonym_options).sum())
    bench = bench[~bench.input.map(has_synonym_options)]  # same text rule as the training slice
    rng = random.Random(SEED)
    (OUT / "bench_images").mkdir(parents=True, exist_ok=True)
    examples, rendered = [], set()
    for qtype, n in (("binary", N_BINARY), ("mcq", N_MCQ), ("captioning", N_CAPTION)):
        pool = bench[bench.type == qtype]
        for row in pool.sample(n=min(n, len(pool)), random_state=SEED).itertuples():
            if row.patch_id not in rendered:
                paths = {b: Path(glob.glob(str(BENCH_S2 / "**" / f"{row.patch_id}_{b}.tif"), recursive=True)[0])
                         for b in ("B02", "B03", "B04")}
                render(read_rgb(paths)).save(OUT / "bench_images" / f"{row.patch_id}.png")
                rendered.add(row.patch_id)
            examples.append({"id": int(row.ID), "patch_id": row.patch_id, "image": f"bench_images/{row.patch_id}.png",
                             "question": row.input, "answer": row.output, "type": row.type,
                             "category": row.category, "country": row.country, "season": row.season})
    rng.shuffle(examples)
    (OUT / "bench.jsonl").write_text("\n".join(json.dumps(e, ensure_ascii=False) for e in examples) + "\n",
                                     encoding="utf-8")
    print(f"bench sample: {len(examples)} examples over {len(rendered)} patches -> {OUT / 'bench.jsonl'} "
          f"({n_synonym} Fall/Autumn questions excluded from the pool)")


def run(args):
    OUT = Path(args.data)
    examples = load_jsonl(OUT / args.bench_file)
    if args.part:
        examples = [e for e in examples if e.get("part") == args.part]
    if args.limit:
        examples = examples[: args.limit]
    model, processor, _ = load_model(adapter=args.adapter)
    model.eval()

    by_cat = defaultdict(lambda: [0, 0])  # category -> [correct, total]
    by_type = defaultdict(lambda: [0, 0])
    unreadable = defaultdict(int)
    mention = {"country": 0, "season": 0}
    n_caption = 0
    samples = []
    replies = []  # every reply, so two runs can be compared example by example (b5_compare.py)
    for i, ex in enumerate(examples):
        is_caption = ex["type"] == "captioning"
        shown = dict(ex, image=ex["pair_image"]) if args.mismatch_image else ex  # same question, another patch's picture
        output = generate(model, processor, OUT, args.size, shown, max_new_tokens=args.caption_tokens if is_caption else 8,
                          blank_image=args.blank_image)
        replies.append({"id": ex["id"], "type": ex["type"], "category": ex["category"], "part": ex.get("part"),
                        "output": output[:300], "parsed": None if is_caption else normalise_choice(output, ex["type"]),
                        "correct": None if is_caption else bool(score_choice(ex, output))})
        if is_caption:
            n_caption += 1
            for k, v in caption_mentions(ex, output).items():
                mention[k] += int(v)
        else:
            ok = score_choice(ex, output)
            by_type[ex["type"]][0] += int(ok)
            by_type[ex["type"]][1] += 1
            by_cat[f'{ex["type"]}/{ex["category"]}'][0] += int(ok)
            by_cat[f'{ex["type"]}/{ex["category"]}'][1] += 1
            if normalise_choice(output, ex["type"]) is None:
                unreadable[ex["type"]] += 1
        if len(samples) < 12:
            samples.append({"type": ex["type"], "question": ex["question"][:160], "reference": ex["answer"][:200],
                            "output": output[:300]})
        if (i + 1) % 100 == 0:
            print(f"{i + 1}/{len(examples)}", flush=True)

    def majority(qtype):
        answers = [normalise_choice(e["answer"], qtype) for e in examples if e["type"] == qtype]
        return max(answers.count(a) for a in set(answers)) / len(answers) if answers else None

    result = {
        "adapter": args.adapter, "blank_image": args.blank_image, "mismatch_image": args.mismatch_image,
        "bench_file": args.bench_file, "part": args.part, "size": args.size, "examples": len(examples),
        "accuracy": {t: {"acc": c / n, "n": n, "chance": 0.5 if t == "binary" else 0.25,
                       "always_answer_the_commonest": majority(t),
                       # An untuned model often answers in sentences, which score as wrong. Accuracy over the
                       # replies that DID contain an answer separates "cannot follow the format" from "wrong".
                       "readable_n": n - unreadable.get(t, 0),
                       "acc_among_readable": c / (n - unreadable[t]) if n - unreadable.get(t, 0) else None}
                     for t, (c, n) in by_type.items()},
        "accuracy_by_category": {k: {"acc": c / n, "n": n} for k, (c, n) in sorted(by_cat.items())},
        "unreadable_replies": dict(unreadable),
        "caption_mentions_rate": {k: v / n_caption for k, v in mention.items()} if n_caption else None,
        "caption_n": n_caption, "samples": samples, "replies": replies,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("accuracy", "unreadable_replies", "caption_mentions_rate")}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prepare").add_argument("--data", default=str(DEFAULT_DATA))
    r = sub.add_parser("run")
    r.add_argument("--data", default=str(DEFAULT_DATA), help="folder holding bench.jsonl and bench_images/")
    r.add_argument("--adapter", default=None)
    r.add_argument("--out", required=True)
    r.add_argument("--size", type=int, default=448)
    r.add_argument("--limit", type=int, default=0)
    r.add_argument("--caption-tokens", type=int, default=200)
    r.add_argument("--bench-file", default="bench.jsonl", help="e.g. bench_hard.jsonl (built by ml/b1_v2.py bench)")
    r.add_argument("--part", default=None, help="restrict to one part of bench_hard: main or heldout")
    r.add_argument("--mismatch-image", action="store_true",
                   help="matched/mismatched test: show the picture of a different patch (needs pair_image)")
    r.add_argument("--blank-image", action="store_true",
                   help="blind baseline: feed a constant grey image instead of the patch (text priors only)")
    a = ap.parse_args()
    prepare(a.data) if a.cmd == "prepare" else run(a)
