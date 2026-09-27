from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field
import uuid


# ─── Request schemas ───────────────────────────────────────────────────────────

class AnalysisCreate(BaseModel):
    notes: Optional[str] = None


# ─── Response schemas ──────────────────────────────────────────────────────────

class ModelScores(BaseModel):
    authentic: float
    synthetic: float
    raw: Optional[dict[str, Any]] = None


class AnalysisResult(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_size_bytes: int
    audio_duration_seconds: float
    sample_rate: int
    verdict: str
    confidence: float
    authentic_probability: Optional[float]
    synthetic_probability: Optional[float]
    raw_scores: Optional[dict[str, Any]]
    model_name: str
    model_version: str
    inference_mode: str
    inference_time_ms: float
    is_demo: bool
    notes: Optional[str]
    spectrogram_path: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnalysisListItem(BaseModel):
    id: str
    original_filename: str
    verdict: str
    confidence: float
    audio_duration_seconds: float
    model_name: str
    inference_mode: str
    is_demo: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PaginatedAnalyses(BaseModel):
    items: list[AnalysisListItem]
    total: int
    page: int
    per_page: int
    pages: int


class HealthResponse(BaseModel):
    status: str
    database: str
    model_available: bool
    model_name: str
    model_version: str
    inference_mode: str
    environment: str
    uptime_seconds: float
    timestamp: datetime


class ModelInfoResponse(BaseModel):
    loaded: bool
    model_name: str
    model_version: str
    architecture: str
    checkpoint_path: Optional[str]
    expected_sample_rate: int
    supported_classes: list[str]
    inference_mode: str
    device: str
    is_demo: bool


class DashboardStats(BaseModel):
    total_analyses: int
    authentic_count: int
    synthetic_count: int
    inconclusive_count: int
    detection_rate: Optional[float]
    recent_analyses: list[AnalysisListItem]
    suspicious_alerts: int
    is_demo_data: bool


class AnalyticsData(BaseModel):
    daily_counts: list[dict]
    verdict_distribution: dict[str, int]
    inference_latency_avg_ms: float
    score_distribution: list[dict]
    is_demo_data: bool
