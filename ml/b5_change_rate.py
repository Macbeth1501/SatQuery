"""How often does the answer change between two runs of the same questions?

    python ml/b5_change_rate.py real.json mismatch.json      # matched vs mismatched image
    python ml/b5_change_rate.py real.json blind.json         # matched vs grey image

Both files are b5_eval.py results (they need the per-example "replies"). Pairs are matched on (type, id). A pair
counts as changed when the two parsed answers differ. A pair where either side is unreadable (`parsed is None`)
is reported in its own bucket and is NOT counted as a change or as agreement: a reply that could not be parsed
says nothing about whether the image mattered. The rate is changed / (changed + unchanged), with a Wilson 95%
interval.

Reading it: a model that ignores the image gives the same answer whatever picture it is shown, so its rate against
a mismatched picture is near 0%. Under greedy decoding a run compared with itself is 0% by construction, so that
is never a reference. This measures whether the picture matters, not whether the answer is right; b5_compare.py
does correctness.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

from b5_compare import wilson


def load_parsed(path):
    """{(type, id): (category, parsed)} for the non-caption replies."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    records = data.get("replies")
    if records is None:
        raise SystemExit(f"{path} has no per-example 'replies'; re-run it with the current b5_eval.py")
    return {(r["type"], r["id"]): (r.get("category"), r["parsed"]) for r in records if r["type"] != "captioning"}


def _summary(changed, unchanged, unreadable):
    n = changed + unchanged
    lo, hi = wilson(changed, n)
    return {"pairs": n + unreadable, "readable_pairs": n, "changed": changed, "unchanged": unchanged,
            "unreadable_either_side": unreadable, "change_rate": changed / n if n else None,
            "ci95": [lo, hi] if n else None}


def change_rate(path_a, path_b):
    a, b = load_parsed(path_a), load_parsed(path_b)
    tally = defaultdict(lambda: [0, 0, 0])  # group -> [changed, unchanged, unreadable]
    for key in sorted(set(a) & set(b)):
        (category, pa), (_, pb) = a[key], b[key]
        slot = 2 if pa is None or pb is None else int(pa == pb)  # 0 changed, 1 unchanged, 2 unreadable
        for group in ("all", key[0], f"{key[0]}/{category}"):
            tally[group][slot] += 1
    return {group: _summary(*counts) for group, counts in sorted(tally.items())}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    args = ap.parse_args()
    print(json.dumps(change_rate(args.a, args.b), indent=1))
