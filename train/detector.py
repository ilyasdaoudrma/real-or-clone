"""Shared inference: used by eval/ and api/ so both score audio exactly the same way."""
import numpy as np
import torch
from transformers import Wav2Vec2ForSequenceClassification

from augment.voicenote import SR, load, trim_edges

WIN_S, HOP_S = 4.0, 2.0
TARGET_DB = -24.0


def prepare(x: np.ndarray) -> np.ndarray:
    """Same level handling as training: trim edge silence, fixed loudness."""
    x = trim_edges(x)
    return (x * 10 ** (TARGET_DB / 20) / (np.sqrt((x ** 2).mean()) + 1e-9)).astype(np.float32)


def normalize(batch: torch.Tensor) -> torch.Tensor:
    """Zero-mean / unit-variance per clip, as the XLS-R feature extractor does."""
    return (batch - batch.mean(-1, keepdim=True)) / (batch.std(-1, keepdim=True) + 1e-7)


class Detector:
    def __init__(self, ckpt: str, device: str | None = None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = Wav2Vec2ForSequenceClassification.from_pretrained(ckpt).to(self.device).eval()

    @torch.inference_mode()
    def score_array(self, x: np.ndarray) -> dict:
        x = prepare(x)
        win, hop = int(WIN_S * SR), int(HOP_S * SR)
        starts = list(range(0, len(x) - win + 1, hop)) if len(x) > win else [0]
        if len(x) > win and starts[-1] + win < len(x):
            starts.append(len(x) - win)  # cover the tail
        chunks = [x[s:s + win] for s in starts]
        batch = normalize(torch.from_numpy(np.stack([np.pad(c, (0, max(0, len(chunks[0]) - len(c))))
                                                      for c in chunks])).to(self.device))
        with torch.autocast(self.device, dtype=torch.bfloat16, enabled=self.device == "cuda"):
            logits = self.model(batch).logits.float()
        p_fake = logits.softmax(-1)[:, 1].cpu().numpy()
        return {
            "p_fake": float(p_fake.mean()),
            "windows": [{"start": round(s / SR, 2), "end": round(min(len(x), s + win) / SR, 2),
                         "p_fake": round(float(p), 4)} for s, p in zip(starts, p_fake)],
            "duration": round(len(x) / SR, 2),
        }

    def score_file(self, path: str) -> dict:
        return self.score_array(load(path))
