"""B1 v3: data/b1_v2 with country, season and climate removed from the caption targets (CPU only, no download).

    python ml/b1_v3.py --src data/b1_v2 --out data/b1_v3

A 120 px Sentinel-2 patch cannot show which country it is in, what season it is, or its climate zone, yet BigEarthNet's
captions state all three, so an adapter trained on them fills them in from memory (run 2 said "Finland, spring" for an
Irish November patch). This keeps every binary and multiple-choice example exactly as in b1_v2 and rewrites only the
captioning rows:

  * the question: each of the 32 caption prompts is mapped to one that asks only for land cover (QUESTION_MAP);
  * the answer: the first sentence loses its "captured during the <season> season in <country>" and "within the
    "<climate>" climate zone" clauses, and any later sentence that still names a country, a nationality, a season or a
    climate is dropped. Those are closing summary sentences ("...the varied landscape of Portugal during the summer
    season"); on b1_v2, 213 sentences go, of which 1 carries an area figure.

The binary and mcq rows are untouched, including the mcq/country, mcq/season and mcq/climate zone questions: the owner
asked for the caption targets, and those rows are balanced by b5_deleak so a text-only model cannot guess them.
Image paths are rewritten to point into the source folder, so no image is copied. `bench_hard.jsonl` is not copied:
evaluation keeps using data/b1_v2/bench_hard.jsonl, so run 2 and run 3 are scored on the same rows.
"""
import argparse
import json
import os
import re
from pathlib import Path

COUNTRIES = ("Lithuania", "Finland", "Ireland", "Portugal", "Austria", "Serbia", "Kosovo", "Luxembourg", "Belgium")
NATIONALITIES = ("Lithuanian", "Finnish", "Irish", "Portuguese", "Austrian", "Serbian", "Kosovar", "Luxembourgish",
                 "Belgian")
_C = "|".join(COUNTRIES)
_S = "spring|summer|fall|autumn|winter"

# Anything a caption may not say about a patch. "fall" counts only as a season ("fall season", "during the fall"),
# because "fall under the broader category of" is common and harmless.
FORBIDDEN = re.compile(
    rf"\b({_C}|{'|'.join(NATIONALITIES)}|spring|summer|autumn|winter|seasons?|seasonal|climate|climatic|boreal|"
    rf"temperate|country|country's|months)\b|\bfall season\b|\b(?:in|during) (?:the )?fall\b",
    re.IGNORECASE,
)
_FIRST_CLAUSES = (
    re.compile(rf",? captured (?:during|in) (?:the )?(?:(?:{_S}) )?(?:season )?(?:in|of) (?:{_C}),"),
    re.compile(rf",? captured in (?:{_C}) (?:during|in) (?:the )?(?:{_S})(?: season)?,"),
    re.compile(r',? (?:within|in|under|characteri[sz]ed by) (?:the |a )?"[^"]*" climate(?: zone)?'),
)
_SENTENCES = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")

# The 32 caption prompts of BigEarthNet.txt (all present in b1_v2) and a land-cover-only version of each.
QUESTION_MAP = {
    "Explain the distribution of land cover in this image, including the geographic region and season.":
        "Explain the distribution of land cover in this image.",
    "Provide a detailed description of the image, specifying the geographic region and land cover types.":
        "Provide a detailed description of the image, specifying the land cover types.",
    "Describe the image, noting where it was captured, the season, and the distribution of land cover types.":
        "Describe the image, noting the distribution of land cover types.",
    "Provide a description of this satellite image, including its geographic location, season, and land cover types.":
        "Provide a description of this satellite image, including its land cover types.",
    "Explain what this image shows, including the region, climate zone, and land cover characteristics.":
        "Explain what this image shows, including its land cover characteristics.",
    "Provide an analysis of the satellite image, mentioning the geographic location, season, and land cover features.":
        "Provide an analysis of the satellite image, mentioning its land cover features.",
    "Give a detailed overview of the image content, including the geographic location and land cover features.":
        "Give a detailed overview of the image content, including its land cover features.",
    "Give a detailed overview of this satellite scene, including the region and land cover classes.":
        "Give a detailed overview of this satellite scene, including its land cover classes.",
    "Provide a summary of the scene, including geographic information, season, and land cover classes.":
        "Provide a summary of the scene, including its land cover classes.",
    "Describe the image, specifying the region, climate, and landscape features.":
        "Describe the image, specifying its landscape features.",
    "Describe the observed landscape, specifying the geographic location, season, and land cover composition.":
        "Describe the observed landscape, specifying its land cover composition.",
    "Explain the content of the image, highlighting the location, seasonal context, and land cover distribution.":
        "Explain the content of the image, highlighting its land cover distribution.",
    "Give a comprehensive overview of the image, specifying the location, climate, and landscape features.":
        "Give a comprehensive overview of the image, specifying its landscape features.",
    "Provide a comprehensive description of the scene, including the location, seasonal context and land cover distribution.":
        "Provide a comprehensive description of the scene, including its land cover distribution.",
    "Describe this satellite image, noting the region, seasonal context, and distribution of land cover types.":
        "Describe this satellite image, noting the distribution of land cover types.",
    "Explain the observed features in the image, specifying the geographic and seasonal context.":
        "Explain the observed land cover features in the image.",
    "Describe this image in detail.": "Describe this image in detail.",
    "Explain the features in the image, highlighting the geographic context, season, and land cover classes.":
        "Explain the features in the image, highlighting its land cover classes.",
    "Describe the satellite scene, including the region, time of year, and land cover classes.":
        "Describe the satellite scene, including its land cover classes.",
    "Describe the content of the image, including the region, climate zone, and land cover distribution.":
        "Describe the content of the image, including its land cover distribution.",
    "Explain the observed land cover and spatial patterns, including the location and climate context.":
        "Explain the observed land cover and spatial patterns.",
    "Explain what can be seen in this satellite image, specifying where and when it was captured.":
        "Explain what land cover can be seen in this satellite image.",
    "Describe this satellite image, including the location, season, and observed land cover.":
        "Describe this satellite image, including the observed land cover.",
    "Describe the content of the satellite image, including where and when it was captured and the landscape composition.":
        "Describe the content of the satellite image, including the landscape composition.",
    "Provide a detailed summary of the scene, including the location and distribution of different land cover types.":
        "Provide a detailed summary of the scene, including the distribution of different land cover types.",
    "Explain what this satellite image shows, mentioning the location, season, and landscape features.":
        "Explain what this satellite image shows, mentioning its landscape features.",
    "Describe the satellite image in detail.": "Describe the satellite image in detail.",
    "Provide a description of this image, including the location, season, and distribution of land cover types.":
        "Provide a description of this image, including the distribution of land cover types.",
    "Provide a detailed description, mentioning the location, seasonal context, and different land covers.":
        "Provide a detailed description, mentioning the different land covers.",
    "Provide an description of the image content, highlighting the geographic location, season, and spatial patterns.":
        "Provide a description of the image content, highlighting its land cover and spatial patterns.",
    "Explain the landscape features visible in this image, including where and when it was captured.":
        "Explain the landscape features visible in this image.",
    "Describe the landscape shown in this satellite image, mentioning the region, climate, and land cover classes.":
        "Describe the landscape shown in this satellite image, mentioning its land cover classes.",
}


def rewrite_caption(answer):
    """(new caption, dropped sentences). The first sentence is always kept, minus its location/time/climate clauses."""
    sentences = _SENTENCES.split(answer.strip())
    first = sentences[0]
    for clause in _FIRST_CLAUSES:
        first = clause.sub("", first)
    kept, dropped = [first], []
    for sentence in sentences[1:]:
        (dropped if FORBIDDEN.search(sentence) else kept).append(sentence)
    return " ".join(kept), dropped


def rewrite_question(question):
    if question not in QUESTION_MAP:
        raise SystemExit(f"caption prompt not in QUESTION_MAP (add it before building): {question!r}")
    return QUESTION_MAP[question]


def convert(rows, image_prefix):
    """Returns (rows, report). Raises SystemExit if any caption still names a country, season or climate."""
    out, dropped, captions = [], [], 0
    for row in rows:
        row = dict(row, image=f"{image_prefix}/{row['image']}")
        if row["type"] == "captioning":
            captions += 1
            answer, gone = rewrite_caption(row["answer"])
            dropped += gone
            row["question"] = rewrite_question(row["question"])
            row["answer"] = answer
            for text in (row["question"], row["answer"]):
                if FORBIDDEN.search(text):
                    raise SystemExit(f"caption {row['id']} still names {FORBIDDEN.search(text).group(0)!r}: {text}")
        out.append(row)
    report = {
        "rows": len(out), "captions": captions, "dropped_sentences": len(dropped),
        "dropped_with_area": sum(("sqm" in s or "square met" in s) for s in dropped),
    }
    return out, report


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--src", default="data/b1_v2")
    ap.add_argument("--out", default="data/b1_v3")
    args = ap.parse_args()
    src, out = Path(args.src), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    prefix = Path(os.path.relpath(src, out)).as_posix()  # images stay in the source folder
    report = {}
    for name in ("train.jsonl", "validation.jsonl"):
        rows = [json.loads(line) for line in (src / name).read_text(encoding="utf-8").splitlines() if line.strip()]
        converted, report[name] = convert(rows, prefix)
        with open(out / name, "w", encoding="utf-8") as f:
            for row in converted:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        missing = [r["image"] for r in converted if not (out / r["image"]).is_file()]
        if missing:
            raise SystemExit(f"{len(missing)} images not found from {out}, e.g. {missing[0]}")
    (out / "b1_v3_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
