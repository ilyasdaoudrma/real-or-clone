"""
Audio preprocessing service.
Handles validation, loading, resampling, and spectrogram generation.
"""
import os
import uuid
import time
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import numpy as np

from app.core.config import settings
from app.core.logging import logger


SUPPORTED_MIME_TYPES = {
    "audio/wav", "audio/wave", "audio/x-wav",
    "audio/mpeg", "audio/mp3",
    "audio/flac", "audio/x-flac",
    "audio/mp4", "audio/x-m4a",
    "audio/ogg", "audio/opus",
    "audio/webm", "video/webm",
    "application/octet-stream",  # fallback for some browsers
}


class AudioValidationError(Exception):
    pass


class AudioService:
    def validate_file(self, filename: str, file_size: int, content_type: str) -> None:
        """Validate audio file before processing."""
        ext = Path(filename).suffix.lower()
        if ext not in settings.SUPPORTED_AUDIO_FORMATS:
            raise AudioValidationError(
                f"Format non supporté: {ext}. "
                f"Formats acceptés: {', '.join(settings.SUPPORTED_AUDIO_FORMATS)}"
            )

        max_size = settings.MAX_AUDIO_SIZE_MB * 1024 * 1024
        if file_size > max_size:
            raise AudioValidationError(
                f"Fichier trop grand: {file_size / 1024 / 1024:.1f} Mo. "
                f"Maximum: {settings.MAX_AUDIO_SIZE_MB} Mo"
            )

    def load_audio(self, file_path: str) -> Tuple[np.ndarray, int, float]:
        """
        Load audio file, resample to target sample rate.
        Returns (audio_array, sample_rate, duration_seconds)
        """
        try:
            import librosa
            audio, sr = librosa.load(
                file_path,
                sr=settings.AUDIO_SAMPLE_RATE,
                mono=True,
            )
            duration = len(audio) / sr

            if duration > settings.MAX_AUDIO_DURATION_SECONDS:
                raise AudioValidationError(
                    f"Audio trop long: {duration:.1f}s. "
                    f"Maximum: {settings.MAX_AUDIO_DURATION_SECONDS}s"
                )

            if duration < 0.5:
                raise AudioValidationError("Audio trop court (minimum 0.5 secondes).")

            logger.info(f"Audio chargé: {duration:.2f}s à {sr}Hz")
            return audio, sr, duration
        except AudioValidationError:
            raise
        except Exception as e:
            raise AudioValidationError(f"Impossible de lire le fichier audio: {e}")

    def generate_spectrogram(self, audio: np.ndarray, sr: int, output_path: str) -> str:
        """Generate and save a spectrogram image."""
        try:
            import librosa
            import librosa.display
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt

            fig, ax = plt.subplots(figsize=(10, 4))
            fig.patch.set_facecolor("#0D172A")
            ax.set_facecolor("#0D172A")

            S = librosa.feature.melspectrogram(y=audio, sr=sr, n_mels=128)
            S_db = librosa.power_to_db(S, ref=np.max)

            img = librosa.display.specshow(
                S_db, sr=sr, x_axis="time", y_axis="mel",
                ax=ax, cmap="magma"
            )
            ax.tick_params(colors="white")
            ax.xaxis.label.set_color("white")
            ax.yaxis.label.set_color("white")
            ax.set_title("Mel-Spectrogram", color="white", fontsize=12)
            plt.colorbar(img, ax=ax, format="%+2.0f dB")

            plt.tight_layout()
            plt.savefig(output_path, dpi=100, facecolor=fig.get_facecolor())
            plt.close(fig)

            return output_path
        except Exception as e:
            logger.warning(f"Impossible de générer le spectrogramme: {e}")
            return None

    def save_upload(self, file_content: bytes, original_filename: str) -> str:
        """Save uploaded file and return path."""
        ext = Path(original_filename).suffix.lower()
        unique_name = f"{uuid.uuid4()}{ext}"
        save_path = os.path.join(settings.UPLOAD_DIR, unique_name)
        with open(save_path, "wb") as f:
            f.write(file_content)
        return save_path, unique_name


audio_service = AudioService()
