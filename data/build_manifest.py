"""Build one manifest CSV of every clip with its label and train/test split.

    python data/build_manifest.py        -> $DATA_DIR/manifest.csv

Columns: path, label (0 real / 1 fake), source, generator, lang, split
Split rules (no leakage):
  * FLEURS real: its own train/dev -> train, test -> test
  * MLAAD fake: whole GENERATORS are held out for test (every commercial API + ~20% of the rest),
    so the test measures generators the model never saw
  * In-the-Wild: all test (out-of-domain, real-world celebrity/politician deepfakes)
  * Our Chatterbox clones: split comes from generate/clone.py (by reference speaker)
"""
import csv
import os
import random
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
DATA_DIR = Path(os.environ.get("DATA_DIR", "~/roc_data")).expanduser()
SEED = 13
HELDOUT_FRACTION = 0.2
# Commercial APIs a scammer would actually use: always held out, never trained on.
HELDOUT_KEYWORDS = ("ElevenLabs", "OpenAI", "Cartesia", "Gemini", "DeepGram", "MiniMax",
                    "minimax", "Inworld", "Hume", "Resemble.ai", "Rime", "Smallest")


def fleurs_rows() -> list[dict]:
    rows = []
    for lang_code, lang in (("en_us", "en"), ("fr_fr", "fr")):
        for split in ("train", "dev", "test"):
            for wav in sorted((DATA_DIR / "fleurs" / lang_code / split).glob("*.wav")):
                rows.append({"path": str(wav), "label": 0, "source": "fleurs", "generator": "real",
                             "lang": lang, "split": "test" if split == "test" else "train"})
    return rows


def mlaad_rows() -> list[dict]:
    sel = DATA_DIR / "mlaad_selected.csv"
    if not sel.exists():
        return []
    with open(sel, encoding="utf-8") as f:
        picked = list(csv.DictReader(f))
    gens = sorted({(r["lang"], r["generator"]) for r in picked})
    rng = random.Random(SEED)
    heldout = {g for g in gens if any(k in g[1] for k in HELDOUT_KEYWORDS)}
    rest = [g for g in gens if g not in heldout]
    heldout |= set(rng.sample(rest, round(len(rest) * HELDOUT_FRACTION)))
    return [{"path": str(DATA_DIR / "mlaad" / r["path"]), "label": 1, "source": "mlaad",
             "generator": r["generator"], "lang": r["lang"],
             "split": "test" if (r["lang"], r["generator"]) in heldout else "train"}
            for r in picked if (DATA_DIR / "mlaad" / r["path"]).exists()]


def itw_rows() -> list[dict]:
    root = DATA_DIR / "itw" / "release_in_the_wild"
    meta = root / "meta.csv"
    if not meta.exists():
        return []
    with open(meta, encoding="utf-8") as f:
        return [{"path": str(root / r["file"]), "label": 0 if r["label"] == "bona-fide" else 1,
                 "source": "itw", "generator": "itw", "lang": "en", "split": "test"}
                for r in csv.DictReader(f)]


def clone_rows() -> list[dict]:
    rows = []
    for shard in sorted(DATA_DIR.glob("clones_shard*.csv")):
        with open(shard, encoding="utf-8") as f:
            rows += [{"path": r["path"], "label": 1, "source": "clones", "generator": "chatterbox-ours",
                      "lang": r["lang"], "split": r["split"]} for r in csv.DictReader(f)]
    return rows


def main() -> None:
    rows = fleurs_rows() + mlaad_rows() + itw_rows() + clone_rows()
    out = DATA_DIR / "manifest.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["path", "label", "source", "generator", "lang", "split"])
        w.writeheader()
        w.writerows(rows)
    counts: dict[tuple, int] = {}
    for r in rows:
        key = (r["source"], r["split"], "fake" if r["label"] else "real")
        counts[key] = counts.get(key, 0) + 1
    for k in sorted(counts):
        print(f"{k[0]:7s} {k[1]:5s} {k[2]:4s} {counts[k]:7d}")
    print(f"-> {out} ({len(rows)} clips)")


if __name__ == "__main__":
    main()
