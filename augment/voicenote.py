"""Turn every clip (real AND fake, same recipe) into a WhatsApp-like voice note.

    sudo apt-get install -y ffmpeg          # once, on Brev
    python augment/voicenote.py             # manifest.csv -> vn/*.wav + manifest_vn.csv
    python augment/voicenote.py --limit 20  # smoke test

Why: without this the detector learns shortcuts ("studio-clean = fake", "long silence = real").
Every clip gets: 16 kHz mono -> edge-silence trim -> random 8 s crop -> random loudness ->
one condition picked from a hash of the path (never from the label):
  clean | opus (16 kbps) | phone (300-3400 Hz, 8 kHz, opus 12 kbps) | noise+opus | reverb+opus
"""
import argparse
import csv
import hashlib
import os
import random
import subprocess
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()
DATA_DIR = Path(os.environ.get("DATA_DIR", "~/roc_data")).expanduser()
SR = 16000
MAX_S = 8.0
TRIM_DB = 40.0            # edge frames this far below the peak count as silence
CONDITIONS = ("clean", "opus", "phone", "noise", "reverb")


def _ffmpeg(args: list[str], data: bytes | None = None) -> bytes:
    # stdin must never be the terminal: a backgrounded ffmpeg that reads the tty gets stopped (hangs forever)
    res = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-threads", "1", *args],
                         input=data if data is not None else b"", capture_output=True, check=True)
    return res.stdout


def load(path: str) -> np.ndarray:
    raw = _ffmpeg(["-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "pipe:1"])
    return np.frombuffer(raw, dtype=np.float32).copy()


def trim_edges(x: np.ndarray) -> np.ndarray:
    frame = SR // 50
    n = len(x) // frame
    if n < 3:
        return x
    rms = np.sqrt((x[: n * frame].reshape(n, frame) ** 2).mean(1) + 1e-12)
    db = 20 * np.log10(rms / rms.max())
    voiced = np.where(db > -TRIM_DB)[0]
    return x[voiced[0] * frame:(voiced[-1] + 1) * frame]


def codec(x: np.ndarray, kbps: int, phone: bool) -> np.ndarray:
    pre = ["-af", "highpass=f=300,lowpass=f=3400", "-ar", "8000"] if phone else []
    enc = _ffmpeg(["-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "pipe:0", *pre,
                   "-c:a", "libopus", "-b:a", f"{kbps}k", "-f", "ogg", "pipe:1"], x.tobytes())
    dec = _ffmpeg(["-i", "pipe:0", "-f", "f32le", "-ac", "1", "-ar", str(SR), "pipe:1"], enc)
    return np.frombuffer(dec, dtype=np.float32).copy()


def add_noise(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    snr_db = rng.uniform(8, 25)
    noise = np.cumsum(rng.standard_normal(len(x))) if rng.random() < 0.5 else rng.standard_normal(len(x))
    noise -= noise.mean()
    scale = np.sqrt((x ** 2).mean() / ((noise ** 2).mean() * 10 ** (snr_db / 10) + 1e-12))
    return x + scale * noise


def add_reverb(x: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    rt60 = rng.uniform(0.2, 0.7)
    t = np.arange(int(rt60 * SR)) / SR
    rir = rng.standard_normal(len(t)) * np.exp(-6.9 * t / rt60)
    rir[0] = 1.0
    y = fftconvolve(x, rir / np.abs(rir).sum() * 4)[: len(x)]  # np.convolve took ~6 s per clip
    return y


def process(row: dict) -> dict | None:
    key = hashlib.sha1(row["path"].encode()).hexdigest()[:16]
    out = DATA_DIR / "vn" / f"{key}.wav"
    rng = np.random.default_rng(int(key, 16) % 2**32)
    cond = CONDITIONS[int(key, 16) % len(CONDITIONS)]
    if not out.exists():
        try:
            x = trim_edges(load(row["path"]))
            if len(x) < SR:  # < 1 s of speech: useless
                return None
            if len(x) > MAX_S * SR:
                start = rng.integers(0, len(x) - int(MAX_S * SR))
                x = x[start:start + int(MAX_S * SR)]
            if cond == "noise":
                x = add_noise(x, rng)
            elif cond == "reverb":
                x = add_reverb(x, rng)
            if cond != "clean":
                x = codec(x.astype(np.float32), 12 if cond == "phone" else 16, cond == "phone")
            target_db = rng.uniform(-30, -18)
            x = x * 10 ** (target_db / 20) / (np.sqrt((x ** 2).mean()) + 1e-9)
            sf.write(out, np.clip(x, -1, 1), SR, subtype="PCM_16")
        except Exception as e:  # corrupt file: report, keep going
            print(f"skip {row['path']}: {e}", flush=True)
            return None
    return {**row, "vn_path": str(out), "aug": cond, "seconds": round(sf.info(out).duration, 2)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    ap.add_argument("--max-test-per-source", type=int, default=4000, help="eval never needs more")
    args = ap.parse_args()
    with open(DATA_DIR / "manifest.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if args.limit:
        rows = rows[:: max(1, len(rows) // args.limit)][: args.limit]
    rng = random.Random(0)
    keep, test_by_src = [r for r in rows if r["split"] != "test"], {}
    for r in rows:
        if r["split"] == "test":
            test_by_src.setdefault(r["source"], []).append(r)
    for src_rows in test_by_src.values():
        keep += rng.sample(src_rows, min(args.max_test_per_source, len(src_rows)))
    rows = keep
    (DATA_DIR / "vn").mkdir(parents=True, exist_ok=True)
    with Pool(args.workers) as pool:
        done = [r for r in tqdm(pool.imap_unordered(process, rows, chunksize=16), total=len(rows)) if r]
    out = DATA_DIR / "manifest_vn.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(done[0].keys()))
        w.writeheader()
        w.writerows(done)
    print(f"{len(done)}/{len(rows)} clips -> {out}")


if __name__ == "__main__":
    main()
