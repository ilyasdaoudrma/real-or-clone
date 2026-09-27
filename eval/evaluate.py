"""Score a trained run on every test group and write results/<run>.json + a markdown table.

    python -m eval.evaluate --run a
    python -m eval.evaluate --run b
    python -m eval.evaluate --run a --max-per-group 50   # smoke test

Test groups (all clips in voice-note form, same as training):
  mlaad_heldout : fake from MLAAD generators never seen in training  vs  real FLEURS test
  itw           : In-the-Wild real vs fake (out-of-domain, never trained on)
  clones        : our Chatterbox clones of held-out speakers  vs  real FLEURS test
Metrics: EER, AUC, and at the fixed 0.5 threshold: false-alarm rate (real flagged as clone)
and miss rate (clone passed as real). Per-generator detection rate for the held-out MLAAD ones.
"""
import argparse
import csv
import json
import os
import random
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import soundfile as sf
from dotenv import load_dotenv
from sklearn.metrics import roc_auc_score, roc_curve

from train.detector import Detector

load_dotenv()
DATA_DIR = Path(os.environ.get("DATA_DIR", "~/roc_data")).expanduser()
THRESHOLD = 0.5


def eer(labels: list[int], scores: list[float]) -> float:
    fpr, tpr, _ = roc_curve(labels, scores)
    fnr = 1 - tpr
    i = int(np.nanargmin(np.abs(fnr - fpr)))
    return float((fpr[i] + fnr[i]) / 2)


def metrics(rows: list[dict]) -> dict:
    y = [int(r["label"]) for r in rows]
    s = [r["p_fake"] for r in rows]
    real = [p for p, l in zip(s, y) if l == 0]
    fake = [p for p, l in zip(s, y) if l == 1]
    return {
        "n_real": len(real), "n_fake": len(fake),
        "eer": round(eer(y, s), 4) if real and fake else None,
        "auc": round(float(roc_auc_score(y, s)), 4) if real and fake else None,
        "false_alarm_rate": round(float(np.mean([p >= THRESHOLD for p in real])), 4) if real else None,
        "miss_rate": round(float(np.mean([p < THRESHOLD for p in fake])), 4) if fake else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", choices=["a", "b", "c"], required=True)
    ap.add_argument("--max-per-group", type=int, default=4000, help="cap per source to keep eval fast")
    args = ap.parse_args()

    with open(DATA_DIR / "manifest_vn.csv", encoding="utf-8") as f:
        test = [r for r in csv.DictReader(f) if r["split"] == "test"]
    by_source: dict[str, list[dict]] = defaultdict(list)
    for r in test:
        by_source[r["source"]].append(r)
    rng = random.Random(0)
    for src, rows in by_source.items():
        if len(rows) > args.max_per_group:
            by_source[src] = rng.sample(rows, args.max_per_group)

    det = Detector(f"checkpoints/run_{args.run}")
    scored: dict[str, list[dict]] = {}
    latencies = []
    for src, rows in by_source.items():
        out = []
        for r in rows:
            x, _ = sf.read(r["vn_path"], dtype="float32")
            t0 = time.perf_counter()
            res = det.score_array(x)
            latencies.append((time.perf_counter() - t0) / max(res["duration"], 0.1) * 10)
            out.append({**r, "p_fake": res["p_fake"]})
        scored[src] = out
        print(f"scored {src}: {len(out)}", flush=True)

    fleurs = scored.get("fleurs", [])
    groups = {
        "voxpopuli_real_false_alarms": scored.get("voxpopuli", []),
        "mlaad_heldout": scored.get("mlaad", []) + fleurs,
        "itw": scored.get("itw", []),
        "clones": scored.get("clones", []) + fleurs,
    }
    results = {"run": args.run, "threshold": THRESHOLD,
               "ms_per_10s_audio": round(1000 * float(np.median(latencies)), 1),
               "groups": {g: metrics(rows) for g, rows in groups.items() if rows}}
    per_gen: dict[str, list[float]] = defaultdict(list)
    for r in scored.get("mlaad", []):
        per_gen[f"{r['lang']}/{r['generator']}"].append(r["p_fake"])
    results["mlaad_heldout_detection_rate"] = {
        g: round(float(np.mean([p >= THRESHOLD for p in ps])), 3) for g, ps in sorted(per_gen.items())}

    out_dir = Path("results")
    out_dir.mkdir(exist_ok=True)
    (out_dir / f"run_{args.run}.json").write_text(json.dumps(results, indent=2))
    print(f"\n| run {args.run} | EER | AUC | false alarms | misses | n real / fake |\n|---|---|---|---|---|---|")
    for g, m in results["groups"].items():
        print(f"| {g} | {m['eer']} | {m['auc']} | {m['false_alarm_rate']} | {m['miss_rate']} | "
              f"{m['n_real']} / {m['n_fake']} |")
    print(f"latency: {results['ms_per_10s_audio']} ms per 10 s of audio -> results/run_{args.run}.json")


if __name__ == "__main__":
    main()
