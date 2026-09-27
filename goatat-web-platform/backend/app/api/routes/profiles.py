import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.database import get_db
from app.models.profile import VoiceProfile, Alert
from app.api.schemas.profile import ProfileCreate, ProfileResponse, AlertResponse, SpeakerVerificationResult
from app.services.audio_service import audio_service, AudioValidationError
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()


def _generate_id():
    return str(uuid.uuid4())


# ─── Profiles ─────────────────────────────────────────────────────────────────

@router.post("/profiles", response_model=ProfileResponse)
async def create_profile(
    display_name: str = Form(...),
    description: Optional[str] = Form(None),
    consent_given: bool = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if not consent_given:
        raise HTTPException(
            status_code=422,
            detail="Le consentement explicite est requis pour créer un profil vocal."
        )

    profile = VoiceProfile(
        id=_generate_id(),
        display_name=display_name,
        description=description,
        consent_given=consent_given,
        consent_timestamp=datetime.utcnow() if consent_given else None,
        is_experimental=True,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return ProfileResponse.model_validate(profile)


@router.get("/profiles", response_model=list[ProfileResponse])
async def list_profiles(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VoiceProfile).order_by(VoiceProfile.created_at.desc()))
    return [ProfileResponse.model_validate(p) for p in result.scalars().all()]


@router.get("/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(profile_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VoiceProfile).where(VoiceProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé")
    return ProfileResponse.model_validate(profile)


@router.delete("/profiles/{profile_id}")
async def delete_profile(profile_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VoiceProfile).where(VoiceProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé")
    await db.delete(profile)
    await db.commit()
    return {"message": "Profil et données associées supprimés"}


@router.post("/profiles/{profile_id}/enroll")
async def enroll_voice(
    profile_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Enroll a voice sample to a profile. Speaker verification is experimental."""
    result = await db.execute(select(VoiceProfile).where(VoiceProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé")
    if not profile.consent_given:
        raise HTTPException(status_code=403, detail="Consentement requis pour l'enrôlement vocal")

    content = await file.read()
    try:
        audio_service.validate_file(file.filename, len(content), file.content_type or "")
    except AudioValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    import os
    file_path, saved_name = audio_service.save_upload(content, file.filename)
    profile.enrollment_filename = saved_name
    profile.has_embedding = False  # Would be set True after embedding extraction
    await db.commit()

    return {
        "message": "Fichier d'enrôlement sauvegardé. L'extraction d'embedding locuteur sera disponible quand le modèle de vérification sera connecté.",
        "profile_id": profile_id,
        "is_experimental": True,
        "warning": "La vérification du locuteur est expérimentale et ne constitue pas une preuve d'identité.",
    }


@router.post("/profiles/{profile_id}/verify", response_model=SpeakerVerificationResult)
async def verify_against_profile(
    profile_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Experimental: verify audio against an enrolled voice profile."""
    result = await db.execute(select(VoiceProfile).where(VoiceProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profil non trouvé")

    import random
    # Placeholder — returns demo similarity score
    similarity = round(random.uniform(0.3, 0.85), 3)
    verdict = "similar" if similarity > 0.65 else "different"

    return SpeakerVerificationResult(
        profile_id=profile_id,
        profile_name=profile.display_name,
        similarity_score=similarity,
        verdict=verdict,
        is_experimental=True,
    )


# ─── Alerts ───────────────────────────────────────────────────────────────────

@router.get("/alerts", response_model=list[AlertResponse])
async def list_alerts(
    severity: Optional[str] = Query(None),
    acknowledged: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Alert).order_by(Alert.created_at.desc())
    if severity:
        query = query.where(Alert.severity == severity)
    if acknowledged is not None:
        query = query.where(Alert.acknowledged == acknowledged)
    result = await db.execute(query)
    return [AlertResponse.model_validate(a) for a in result.scalars().all()]


@router.patch("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerte non trouvée")
    alert.acknowledged = True
    alert.acknowledged_at = datetime.utcnow()
    await db.commit()
    return {"message": "Alerte acquittée"}


@router.patch("/alerts/{alert_id}/dismiss")
async def dismiss_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alerte non trouvée")
    alert.dismissed = True
    await db.commit()
    return {"message": "Alerte ignorée"}
