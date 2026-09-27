"""
XLS-R 300M inference service integration layer.
This module provides the interface for the GOATAT fine-tuned XLS-R model.
Connect the trained checkpoint by setting MODEL_PATH in .env and USE_DEMO_MODE=False.
"""
from typing import Optional
from app.core.config import settings
from app.core.logging import logger


class XLSRInferenceService:
    """
    Production inference service for the GOATAT fine-tuned XLS-R 300M model.
    
    Expected model output:
        Two-class classifier: [authentic, synthetic]
        Input: 16kHz mono audio waveform (numpy array)
        Output: dict with probabilities and logits
    
    To activate:
        1. Set MODEL_PATH=/path/to/checkpoint in .env
        2. Set USE_DEMO_MODE=False in .env
        3. Ensure PyTorch and Hugging Face Transformers are installed
    """

    ARCHITECTURE = "facebook/wav2vec2-xls-r-300m"
    SUPPORTED_CLASSES = ["authentic", "synthetic"]
    EXPECTED_SAMPLE_RATE = 16000

    def __init__(self, model_path: str, device: str = "cpu"):
        self.model_path = model_path
        self.device = device
        self.model = None
        self.processor = None
        self.is_loaded = False
        self._load_model()

    def _load_model(self):
        try:
            import torch
            from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

            logger.info(f"Chargement du modèle XLS-R depuis {self.model_path}")
            self.processor = AutoFeatureExtractor.from_pretrained(self.model_path)
            self.model = AutoModelForAudioClassification.from_pretrained(self.model_path)
            self.model.to(self.device)
            self.model.eval()
            self.is_loaded = True
            logger.info("Modèle XLS-R chargé avec succès")
        except Exception as e:
            logger.error(f"Échec du chargement du modèle: {e}")
            self.is_loaded = False
            raise

    def predict(self, audio_array, sample_rate: int) -> dict:
        if not self.is_loaded:
            raise RuntimeError("Le modèle XLS-R n'est pas chargé.")

        import torch
        import time

        start = time.perf_counter()

        inputs = self.processor(
            audio_array,
            sampling_rate=self.EXPECTED_SAMPLE_RATE,
            return_tensors="pt",
            padding=True,
        )
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1).squeeze().tolist()

        if isinstance(probs, float):
            probs = [probs, 1 - probs]

        # Map to class labels
        id2label = self.model.config.id2label
        class_labels = [id2label.get(i, str(i)) for i in range(len(probs))]

        # Build probability dict
        prob_dict = {label: round(prob, 4) for label, prob in zip(class_labels, probs)}

        authentic_prob = prob_dict.get("authentic", prob_dict.get("real", probs[0]))
        synthetic_prob = prob_dict.get("synthetic", prob_dict.get("fake", probs[1]))

        confidence = max(authentic_prob, synthetic_prob)

        if synthetic_prob > 0.75:
            verdict = "synthetic"
        elif synthetic_prob > 0.45:
            verdict = "inconclusive"
        else:
            verdict = "authentic"

        elapsed_ms = (time.perf_counter() - start) * 1000

        return {
            "verdict": verdict,
            "confidence": round(confidence, 4),
            "authentic_probability": round(authentic_prob, 4),
            "synthetic_probability": round(synthetic_prob, 4),
            "raw_scores": {
                "logits": [round(float(l), 4) for l in logits.squeeze().tolist()],
                "probabilities": prob_dict,
            },
            "model_name": f"XLS-R 300M (GOATAT fine-tuned) — {self.model_path}",
            "model_version": settings.MODEL_VERSION,
            "inference_mode": "production",
            "inference_time_ms": round(elapsed_ms, 2),
            "is_demo": False,
        }
