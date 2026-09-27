from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.database import Base
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    audio_duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    sample_rate: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Model results
    verdict: Mapped[str] = mapped_column(String(50), nullable=False)  # authentic, synthetic, inconclusive
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    authentic_probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    synthetic_probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    raw_scores: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Model info
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    inference_mode: Mapped[str] = mapped_column(String(50), nullable=False)  # demo, production
    inference_time_ms: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Metadata
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    spectrogram_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
