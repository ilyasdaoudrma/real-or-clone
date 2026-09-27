"""
Demo inference service.
Returns realistic-looking but entirely synthetic predictions for local development.
All results are clearly marked as demo/non-production.
"""
import random
import math
import time
from typing import Optional
from app.core.logging import logger


class DemoInferenceService:
    """
    Simulates the output of an XLS-R-based voice authenticity classifier.
    Should be replaced by XLSRInferenceService when the trained model is available.
    """

    MODEL_NAME = "XLS-R 300M (GOATAT — mode démo)"
    MODEL_VERSION = "0.0.0-demo"
    INFERENCE_MODE = "demo"

    def __init__(self):
        logger.info("DemoInferenceService initialisé — mode démonstration actif")

    def predict(self, audio_array, sample_rate: int) -> dict:
        """
        Simulate a voice authenticity prediction.
        The result is clearly marked as demo data.
        """
        start = time.perf_counter()

        # Simulate variable inference latency
        simulated_latency = random.uniform(0.3, 1.8)
        time.sleep(simulated_latency)

        # Generate plausible scores based on audio energy (very rough heuristic)
        try:
            import numpy as np
            energy = float(np.mean(np.abs(audio_array)))
            seed_value = int(energy * 1e6) % 100
        except Exception:
            seed_value = random.randint(0, 100)

        random.seed(seed_value + int(time.time()) % 100)

        # Generate synthetic probability with some variation
        synthetic_prob = random.betavariate(2, 5)  # skew toward authentic in demo
        authentic_prob = 1.0 - synthetic_prob

        # Verdict determination
        if synthetic_prob > 0.75:
            verdict = "synthetic"
        elif synthetic_prob > 0.45:
            verdict = "inconclusive"
        else:
            verdict = "authentic"

        confidence = max(authentic_prob, synthetic_prob)

        elapsed_ms = (time.perf_counter() - start) * 1000

        return {
            "verdict": verdict,
            "confidence": round(confidence, 4),
            "authentic_probability": round(authentic_prob, 4),
            "synthetic_probability": round(synthetic_prob, 4),
            "raw_scores": {
                "logit_authentic": round(math.log(authentic_prob / (1 - authentic_prob + 1e-9)), 4),
                "logit_synthetic": round(math.log(synthetic_prob / (1 - synthetic_prob + 1e-9)), 4),
            },
            "model_name": self.MODEL_NAME,
            "model_version": self.MODEL_VERSION,
            "inference_mode": self.INFERENCE_MODE,
            "inference_time_ms": round(elapsed_ms, 2),
            "is_demo": True,
        }
