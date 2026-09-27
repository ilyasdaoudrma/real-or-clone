from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.core.logging import logger
from app.models.database import init_db
from app.api.routes import health, analysis, profiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 GOATAT Real or Clone API démarrage...")
    await init_db()
    logger.info("✅ Base de données initialisée")

    # Warm up inference service
    from app.services.inference_service import get_inference_service
    try:
        svc = get_inference_service()
        logger.info(f"✅ Service d'inférence prêt: {svc.__class__.__name__}")
    except Exception as e:
        logger.warning(f"⚠️ Service d'inférence non disponible: {e}")

    yield
    logger.info("👋 GOATAT API arrêt")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "API REST pour la plateforme GOATAT — Real or Clone. "
        "Détection de voix synthétiques, clonage vocal, et deepfake audio."
    ),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files for uploads
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Routes
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(analysis.router, prefix="/api/v1", tags=["Analyse vocale"])
app.include_router(profiles.router, prefix="/api/v1", tags=["Profils & Alertes"])


@app.get("/")
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
        "status": "running",
    }
