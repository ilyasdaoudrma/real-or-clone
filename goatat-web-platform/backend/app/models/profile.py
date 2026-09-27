from datetime import datetime
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Text, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.models.database import Base
import uuid


def generate_uuid():
    return str(uuid.uuid4())


class VoiceProfile(Base):
    __tablename__ = "voice_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    enrollment_filename: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    embedding_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    embedding_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    has_embedding: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_experimental: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    analysis_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)  # critical, high, medium, low
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
