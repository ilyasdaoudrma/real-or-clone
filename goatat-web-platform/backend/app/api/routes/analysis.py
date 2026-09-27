import os
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

from app.models.database import get_db
from app.models.analysis import Analysis
from app.models.profile import Alert
from app.api.schemas.analysis import (
    AnalysisResult, AnalysisListItem, PaginatedAnalyses, DashboardStats, AnalyticsData
)
from app.services.audio_service import audio_service, AudioValidationError
from app.services.inference_service import get_inference_service
from app.services.analytics_service import analytics_service
from app.core.config import settings
from app.core.logging import logger

router = APIRouter()


def _generate_id():
    return str(uuid.uuid4())


@router.post("/analysis", response_model=AnalysisResult)
async def create_analysis(
    file: UploadFile = File(...),
    notes: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload and analyze an audio file for voice authenticity."""
    content = await file.read()
    file_size = len(content)

    # Validate
    try:
        audio_service.validate_file(file.filename, file_size, file.content_type or "")
    except AudioValidationError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Save file
    try:
        file_path, saved_name = audio_service.save_upload(content, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur de sauvegarde: {e}")

    # Load audio
    try:
        audio_array, sample_rate, duration = audio_service.load_audio(file_path)
    except AudioValidationError as e:
        os.remove(file_path)
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Erreur de traitement audio: {e}")

    # Generate spectrogram
    spec_path = os.path.join(settings.UPLOAD_DIR, f"spec_{saved_name}.png")
    audio_service.generate_spectrogram(audio_array, sample_rate, spec_path)

    # Run inference
    try:
        service = get_inference_service()
        result = service.predict(audio_array, sample_rate)
    except Exception as e:
        logger.error(f"Erreur d'inférence: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur d'inférence: {e}")

    # Persist to DB
    analysis_id = _generate_id()
    analysis = Analysis(
        id=analysis_id,
        filename=saved_name,
        original_filename=file.filename,
        file_size_bytes=file_size,
        audio_duration_seconds=round(duration, 3),
        sample_rate=sample_rate,
        verdict=result["verdict"],
        confidence=result["confidence"],
        authentic_probability=result.get("authentic_probability"),
        synthetic_probability=result.get("synthetic_probability"),
        raw_scores=result.get("raw_scores"),
        model_name=result["model_name"],
        model_version=result["model_version"],
        inference_mode=result["inference_mode"],
        inference_time_ms=result["inference_time_ms"],
        is_demo=result["is_demo"],
        notes=notes,
        spectrogram_path=spec_path if os.path.exists(spec_path) else None,
    )
    db.add(analysis)

    # Create alert if synthetic and above threshold
    if result["verdict"] == "synthetic" and result["confidence"] >= settings.SYNTHETIC_ALERT_THRESHOLD:
        alert = Alert(
            id=_generate_id(),
            analysis_id=analysis_id,
            severity="high" if result["confidence"] >= 0.9 else "medium",
            title="Voix synthétique suspectée",
            description=(
                f"L'analyse du fichier « {file.filename} » indique une probabilité élevée "
                f"de voix synthétique ({result['confidence']*100:.1f}%). "
                f"Résultat généré par le modèle — ne constitue pas une preuve."
            ),
            confidence=result["confidence"],
        )
        db.add(alert)

    await db.commit()
    await db.refresh(analysis)
    return AnalysisResult.model_validate(analysis)


@router.get("/analysis", response_model=PaginatedAnalyses)
async def list_analyses(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    verdict: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Analysis).order_by(Analysis.created_at.desc())
    count_query = select(func.count(Analysis.id))

    if search:
        query = query.where(Analysis.original_filename.ilike(f"%{search}%"))
        count_query = count_query.where(Analysis.original_filename.ilike(f"%{search}%"))

    if verdict and verdict in ("authentic", "synthetic", "inconclusive"):
        query = query.where(Analysis.verdict == verdict)
        count_query = count_query.where(Analysis.verdict == verdict)

    total = await db.scalar(count_query) or 0
    offset = (page - 1) * per_page
    result = await db.execute(query.offset(offset).limit(per_page))
    items = result.scalars().all()

    return PaginatedAnalyses(
        items=[AnalysisListItem.model_validate(a) for a in items],
        total=total,
        page=page,
        per_page=per_page,
        pages=max(1, -(-total // per_page)),
    )


@router.get("/analysis/{analysis_id}", response_model=AnalysisResult)
async def get_analysis(analysis_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analyse non trouvée")
    return AnalysisResult.model_validate(analysis)


@router.delete("/analysis/{analysis_id}")
async def delete_analysis(analysis_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analyse non trouvée")

    # Remove files
    for path in [
        os.path.join(settings.UPLOAD_DIR, analysis.filename),
        analysis.spectrogram_path,
    ]:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

    await db.delete(analysis)
    await db.commit()
    return {"message": "Analyse supprimée"}


@router.get("/dashboard/stats", response_model=DashboardStats)
async def dashboard_stats(db: AsyncSession = Depends(get_db)):
    stats = await analytics_service.get_dashboard_stats(db)
    from app.api.schemas.analysis import AnalysisListItem
    stats["recent_analyses"] = [AnalysisListItem.model_validate(a) for a in stats["recent_analyses"]]
    return DashboardStats(**stats)


@router.get("/analytics", response_model=AnalyticsData)
async def analytics(days: int = Query(30, ge=1, le=365), db: AsyncSession = Depends(get_db)):
    data = await analytics_service.get_analytics_data(db, days)
    return AnalyticsData(**data)


@router.get("/analysis/{analysis_id}/spectrogram")
async def get_spectrogram(analysis_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = result.scalar_one_or_none()
    if not analysis or not analysis.spectrogram_path:
        raise HTTPException(status_code=404, detail="Spectrogramme non disponible")
    if not os.path.exists(analysis.spectrogram_path):
        raise HTTPException(status_code=404, detail="Fichier spectrogramme introuvable")
    return FileResponse(analysis.spectrogram_path, media_type="image/png")
