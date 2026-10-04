"""
DocuSentinel AI - FastAPI Application Entry Point
Intelligent Document Investigation Platform
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import get_settings
from backend.database import init_db
from backend.routes import documents, investigate, conflicts, evidence, health

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("docusentinel")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle: startup and shutdown."""
    logger.info("DocuSentinel AI starting up...")
    # Initialize database tables
    await init_db()
    # Ensure upload directory exists
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.vectorstore_path.mkdir(parents=True, exist_ok=True)
    logger.info("Database initialized.")
    logger.info("DocuSentinel AI ready.")
    yield
    logger.info("DocuSentinel AI shutting down.")


app = FastAPI(
    title="DocuSentinel AI",
    description="Intelligent Document Investigation Platform — Evidence-first AI with conflict detection.",
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(investigate.router, prefix="/api", tags=["Investigate"])
app.include_router(conflicts.router, prefix="/api/conflicts", tags=["Conflicts"])
app.include_router(evidence.router, prefix="/api/evidence", tags=["Evidence"])


@app.get("/")
async def root():
    return {
        "app": "DocuSentinel AI",
        "version": settings.app_version,
        "tagline": "Investigate documents. Trace evidence. Detect conflicts. Trust the answer.",
        "docs": "/api/docs",
    }
