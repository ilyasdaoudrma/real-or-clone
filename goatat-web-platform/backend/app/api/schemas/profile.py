from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ProfileCreate(BaseModel):
    display_name: str
    description: Optional[str] = None
    consent_given: bool = False


class ProfileResponse(BaseModel):
    id: str
    display_name: str
    description: Optional[str]
    has_embedding: bool
    consent_given: bool
    consent_timestamp: Optional[datetime]
    is_experimental: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    id: str
    analysis_id: Optional[str]
    severity: str
    title: str
    description: str
    confidence: Optional[float]
    acknowledged: bool
    dismissed: bool
    created_at: datetime
    acknowledged_at: Optional[datetime]

    class Config:
        from_attributes = True


class SpeakerVerificationResult(BaseModel):
    profile_id: str
    profile_name: str
    similarity_score: float
    verdict: str
    is_experimental: bool = True
    warning: str = (
        "La vérification du locuteur est expérimentale et ne constitue pas une preuve d'identité."
    )
