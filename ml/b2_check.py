"""B2 checks against a running model server (ml/serve_vqa.py); plain HTTP, no torch.

    python ml/b2_check.py answers --out <file.json> [--adapter run2]   # the 23 live-demo questions
    python ml/b2_check.py diff <before.json> <after.json>                 # must be identical
    python ml/b2_check.py latency --rounds 5                              # run2 -> run3 -> base, back to back

`answers` asks every question of every live-demo patch (frontend/src/data/realSamples.json) about that patch's
GeoTIFF, the file the studio uploads, through POST /vqa. A server that predates multi-adapter serving ignores the
`adapter` field, so the same command records the before and the after.

`latency` is the ML_PLAN G-B2 criterion: with both adapters resident, a call on run3 straight after a call on run2
(and base straight after run3) must not be slower than a repeat call on the same adapter. It alternates
adapters in a fixed cycle after one warm-up call each, and reports the median per (previous, current) pair from
the server's own `latency_ms`, which times generation only, plus the client round trip.
"""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "frontend" / "src" / "data" / "realSamples.json"
REAL = ROOT / "frontend" / "public" / "real"


def questions():
    for sample in json.loads(SAMPLES.read_text(encoding="utf-8"))["samples"]:
        for q in sample["questions"]:
            yield sample, q


def cmd_answers(args):
    rows = []
    with httpx.Client(base_url=args.url, timeout=120) as client:
        for sample, q in questions():
            body = {"image_path": str(REAL / sample["rasterFile"]), "question": q["question"]}
            if args.adapter:
                body["adapter"] = args.adapter
            reply = client.post("/vqa", json=body)
            reply.raise_for_status()
            r = reply.json()
            rows.append({"sample": sample["id"], "question": q["question"], "reference": q["answer"],
                         "answer": r["answer"], "distribution": r["distribution"], "raw_output": r["raw_output"],
                         "adapter_id": r["adapter_id"]})
    correct = sum(r["answer"] == r["reference"] for r in rows)
    out = {"server": args.url, "adapter_requested": args.adapter, "n": len(rows), "matches_reference": correct,
           "rows": rows}
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"{len(rows)} questions, {correct} match the reference; written to {args.out}")


def cmd_diff(args):
    a, b = (json.loads(Path(p).read_text(encoding="utf-8"))["rows"] for p in (args.before, args.after))
    if len(a) != len(b):
        sys.exit(f"different lengths: {len(a)} vs {len(b)}")
    changed = [(x, y) for x, y in zip(a, b)
               if (x["question"], x["answer"], x["distribution"], x["raw_output"])
               != (y["question"], y["answer"], y["distribution"], y["raw_output"])]
    for x, y in changed:
        print(f"CHANGED {x['sample']}: {x['question'][:60]}\n  {x['distribution']} -> {y['distribution']}")
    print(f"{len(a)} compared, {len(changed)} changed (answer, full distribution and raw reply)")
    sys.exit(1 if changed else 0)


def cmd_latency(args):
    sample, q = next(iter(questions()))
    image = str(REAL / sample["rasterFile"])
    cycle = ["run2", "run3", "base"]
    timings = {}
    with httpx.Client(base_url=args.url, timeout=120) as client:
        adapters = client.get("/adapters").json()
        resident = [a["name"] for a in adapters["adapters"]]
        print(f"resident adapters: {resident}")

        def call(name):
            body = {"image_path": image, "question": q["question"], "adapter": name, "task": "vqa"}
            t0 = time.perf_counter()
            reply = client.post("/infer", json=body)
            reply.raise_for_status()
            return reply.json()["latency_ms"], (time.perf_counter() - t0) * 1000.0

        for name in cycle:  # warm-up: first use of each path, not timed
            call(name)
        previous = cycle[-1]
        sequence = cycle * args.rounds + [n for n in cycle for _ in range(args.rounds)]  # switching, then repeats
        for name in sequence:
            server_ms, client_ms = call(name)
            timings.setdefault(f"{previous}->{name}", []).append((server_ms, client_ms))
            previous = name
        health = client.get("/health").json()
    report = {"question": q["question"], "rounds": args.rounds, "resident": resident, "pairs": {}}
    for pair, values in sorted(timings.items()):
        report["pairs"][pair] = {"n": len(values),
                                 "median_server_ms": round(statistics.median(v[0] for v in values), 1),
                                 "median_client_ms": round(statistics.median(v[1] for v in values), 1),
                                 "max_server_ms": round(max(v[0] for v in values), 1)}
    report["gpu"] = health.get("gpu")
    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--url", default="http://127.0.0.1:8001")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("answers")
    a.add_argument("--out", required=True)
    a.add_argument("--adapter", default=None)
    a.set_defaults(func=cmd_answers)
    d = sub.add_parser("diff")
    d.add_argument("before")
    d.add_argument("after")
    d.set_defaults(func=cmd_diff)
    lat = sub.add_parser("latency")
    lat.add_argument("--rounds", type=int, default=5)
    lat.add_argument("--out", default=None)
    lat.set_defaults(func=cmd_latency)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
