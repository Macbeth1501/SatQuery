"""Paired comparison of two runs on the same examples: McNemar's exact test on per-example correctness.

    python ml/b5_compare.py A.json B.json                # A = result of b5_eval.py, or of b5_text_only.py score
    python ml/b5_compare.py tuned.json text_only.json --part main

Unpaired differences of two 400-example scores carry about 3.4 points of noise each; pairing on the example
removes the part of the noise that comes from some questions being easy. Both files must hold per-example
records ("replies" from b5_eval.py, "records" from b5_text_only.py) with the same example ids.

The test uses only the discordant pairs: b = A right and B wrong, c = A wrong and B right. Under the null
hypothesis that neither run is better each discordant pair is a fair coin, so the exact two-sided p-value is a
binomial tail. The confidence interval is the Newcombe-Wilson-style interval on the paired difference (b - c) / n
via the Wilson interval on b / (b + c), scaled by the discordant share; it is approximate.
"""
import argparse
import json
import math
from pathlib import Path


def mcnemar_exact(b, c):
    """Two-sided exact p-value for b and c discordant pairs."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def wilson(k, n, z=1.96):
    if n == 0:
        return 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return centre - half, centre + half


def paired(a, b):
    """a, b: {example id: bool correct}. Returns the paired summary over the ids both runs have."""
    ids = sorted(set(a) & set(b))
    n = len(ids)
    both = sum(a[i] and b[i] for i in ids)
    only_a = sum(a[i] and not b[i] for i in ids)
    only_b = sum(b[i] and not a[i] for i in ids)
    neither = n - both - only_a - only_b
    diff = (only_a - only_b) / n if n else float("nan")
    lo, hi = wilson(only_a, only_a + only_b)
    disc = (only_a + only_b) / n if n else 0.0
    return {"n": n, "a_acc": (both + only_a) / n if n else None, "b_acc": (both + only_b) / n if n else None,
            "diff_a_minus_b": diff, "diff_ci95": [(2 * lo - 1) * disc, (2 * hi - 1) * disc],
            "only_a_right": only_a, "only_b_right": only_b, "both_right": both, "neither_right": neither,
            "p_value": mcnemar_exact(only_a, only_b)}


def load_correct(path, part=None):
    """{(type, id): correct} from either result format."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    records = data.get("replies") or data.get("records")
    if records is None:
        raise SystemExit(f"{path} has no per-example records ('replies' or 'records'); re-run it with the current "
                         "b5_eval.py / b5_text_only.py")
    out = {}
    for r in records:
        if r["correct"] is None or (part and r.get("part") not in (None, part)):
            continue
        out[(r["type"], r["id"])] = bool(r["correct"])
    return out


def compare(path_a, path_b, part=None):
    a, b = load_correct(path_a, part), load_correct(path_b, part)
    result = {}
    for qtype in ("binary", "mcq"):
        sub_a = {k[1]: v for k, v in a.items() if k[0] == qtype}
        sub_b = {k[1]: v for k, v in b.items() if k[0] == qtype}
        result[qtype] = paired(sub_a, sub_b)
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--part", default=None, help="restrict to one part of bench_hard (main / heldout)")
    args = ap.parse_args()
    print(json.dumps(compare(args.a, args.b, args.part), indent=1))
