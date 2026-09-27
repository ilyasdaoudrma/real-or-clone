"""
Inference service factory.
Selects the appropriate inference backend (demo vs production XLS-R).
"""
from typing import Optional
from app.core.config import settings
from app.core.logging import logger


_inference_service = None


def get_inference_service():
    global _inference_service
    if _inference_service is None:
        _inference_service = _create_inference_service()
    return _inference_service


def _create_inference_service():
    if settings.USE_DEMO_MODE or not settings.MODEL_PATH:
        logger.warning(
            "USE_DEMO_MODE=True ou MODEL_PATH non défini — "
            "utilisation du service de démonstration. "
            "Les prédictions ne sont PAS des résultats de modèle réels."
        )
        from app.services.demo_inference import DemoInferenceService
        return DemoInferenceService()
    else:
        try:
            from app.services.xlsr_model import XLSRInferenceService
            return XLSRInferenceService(
                model_path=settings.MODEL_PATH,
                device=settings.INFERENCE_DEVICE,
            )
        except Exception as e:
            logger.error(f"Impossible de charger le modèle XLS-R: {e}. Repli sur le mode démo.")
            from app.services.demo_inference import DemoInferenceService
            return DemoInferenceService()


def get_model_info() -> dict:
    service = get_inference_service()
    from app.services.demo_inference import DemoInferenceService
    is_demo = isinstance(service, DemoInferenceService)

    return {
        "loaded": True,
        "model_name": settings.MODEL_NAME if not is_demo else service.MODEL_NAME,
        "model_version": settings.MODEL_VERSION if not is_demo else service.MODEL_VERSION,
        "architecture": "facebook/wav2vec2-xls-r-300m",
        "checkpoint_path": settings.MODEL_PATH,
        "expected_sample_rate": settings.AUDIO_SAMPLE_RATE,
        "supported_classes": ["authentic", "synthetic"],
        "inference_mode": "demo" if is_demo else "production",
        "device": settings.INFERENCE_DEVICE,
        "is_demo": is_demo,
    }
