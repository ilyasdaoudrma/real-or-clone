import time
from datetime import datetime
from fastapi import APIRouter
from app.api.schemas.analysis import HealthResponse, ModelInfoResponse
from app.services.inference_service import get_model_info
from app.core.config import settings

router = APIRouter()
_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="ok",
        database="connected",
        model_available=True,
        model_name=settings.MODEL_NAME,
        model_version=settings.MODEL_VERSION,
        inference_mode="demo" if settings.USE_DEMO_MODE else "production",
        environment=settings.ENVIRONMENT,
        uptime_seconds=round(time.time() - _start_time, 1),
        timestamp=datetime.utcnow(),
    )


@router.get("/model/info", response_model=ModelInfoResponse)
async def model_info():
    info = get_model_info()
    return ModelInfoResponse(**info)
