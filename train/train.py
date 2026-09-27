"""Fine-tune XLS-R 300M as a real/fake classifier on voice-note clips.

    python -m train.train --run a            # baseline: public data only
    python -m train.train --run b            # + our fresh Chatterbox clones
    python -m train.train --run c            # + varied real speech (VoxPopuli) + In-the-Wild train speakers
    python -m train.train --run a --max-steps 20 --batch 4   # smoke test (3060)

Saves checkpoints/run_<a|b>/ (HF format, loadable by train.detector.Detector).
"""
import argparse
import csv
import json
import os
import random
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from dotenv import load_dotenv
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from transformers import Wav2Vec2ForSequenceClassification

from train.detector import SR, normalize

load_dotenv()
DATA_DIR = Path(os.environ.get("DATA_DIR", "~/roc_data")).expanduser()
BASE = "facebook/wav2vec2-xls-r-300m"
CROP_S = 4.0


class Clips(Dataset):
    def __init__(self, rows: list[dict]):
        self.rows = rows
        self.n = int(CROP_S * SR)

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, i: int):
        x, _ = sf.read(self.rows[i]["vn_path"], dtype="float32")
        if len(x) > self.n:
            s = random.randint(0, len(x) - self.n)
            x = x[s:s + self.n]
        elif len(x) < self.n:
            x = np.tile(x, int(np.ceil(self.n / len(x))))[: self.n]
        return torch.from_numpy(x), int(self.rows[i]["label"])


def load_rows(run: str) -> list[dict]:
    with open(DATA_DIR / "manifest_vn.csv", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["split"] == "train"]
    excluded = {"a": {"clones", "itw", "voxpopuli"}, "b": {"itw", "voxpopuli"}, "c": set()}[run]
    return [r for r in rows if r["source"] not in excluded]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", choices=["a", "b", "c"], required=True)
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--batch", type=int, default=32)
    ap.add_argument("--lr", type=float, default=3e-5)
    ap.add_argument("--max-steps", type=int, default=0)
    ap.add_argument("--workers", type=int, default=min(12, os.cpu_count() or 2))
    args = ap.parse_args()
    torch.manual_seed(0)
    random.seed(0)

    rows = load_rows(args.run)
    labels = [int(r["label"]) for r in rows]
    n_fake = sum(labels)
    n_real = len(labels) - n_fake
    print(f"run {args.run}: {len(rows)} train clips ({n_real} real / {n_fake} fake)")
    # Balanced batches: each class drawn with equal probability.
    weights = [0.5 / n_fake if y else 0.5 / n_real for y in labels]
    sampler = WeightedRandomSampler(weights, num_samples=len(rows), replacement=True)
    loader = DataLoader(Clips(rows), batch_size=args.batch, sampler=sampler, num_workers=args.workers,
                        pin_memory=True, drop_last=True, persistent_workers=args.workers > 0)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = Wav2Vec2ForSequenceClassification.from_pretrained(
        BASE, num_labels=2, label2id={"real": 0, "fake": 1}, id2label={0: "real", 1: "fake"}).to(device)
    model.freeze_feature_encoder()
    head = [p for n, p in model.named_parameters() if n.startswith(("projector", "classifier"))]
    body = [p for n, p in model.named_parameters() if p.requires_grad and not n.startswith(("projector", "classifier"))]
    opt = torch.optim.AdamW([{"params": body, "lr": args.lr}, {"params": head, "lr": args.lr * 20}],
                            weight_decay=0.01)
    total = args.max_steps or int(args.epochs * len(loader))
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=[args.lr, args.lr * 20], total_steps=total,
                                                pct_start=0.1)

    model.train()
    step, t0, run_loss, run_acc, seen = 0, time.time(), 0.0, 0.0, 0
    while step < total:
        for x, y in loader:
            x, y = normalize(x.to(device, non_blocking=True)), y.to(device)
            with torch.autocast(device, dtype=torch.bfloat16, enabled=device == "cuda"):
                out = model(x, labels=y)
            out.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad(set_to_none=True)
            step += 1
            run_loss += out.loss.item()
            run_acc += (out.logits.argmax(-1) == y).float().mean().item()
            seen += 1
            if step % 25 == 0 or step == total:
                el = time.time() - t0
                print(f"step {step}/{total} loss {run_loss / seen:.4f} acc {run_acc / seen:.3f} "
                      f"{el / step:.2f}s/step eta {(total - step) * el / step / 60:.1f} min", flush=True)
                run_loss, run_acc, seen = 0.0, 0.0, 0
            if step >= total:
                break

    out_dir = Path("checkpoints") / f"run_{args.run}"
    model.save_pretrained(out_dir)
    (out_dir / "train_info.json").write_text(json.dumps({
        "run": args.run, "train_clips": len(rows), "real": n_real, "fake": n_fake, "steps": total,
        "batch": args.batch, "lr": args.lr, "minutes": round((time.time() - t0) / 60, 1)}, indent=2))
    print(f"saved -> {out_dir}")


if __name__ == "__main__":
    main()
