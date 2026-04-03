"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from app.api.routes import health, transcribe, jobs, fact_check
from app.services.model_loader import initialize_models
from app.utils.logger import setup_logger
from app.core.config import settings
import os

logger = setup_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("Starting YouTube Transcription Service...")
    import torch
    _device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Whisper model: {settings.get_whisper_model_size(_device)} (device: {_device})")
    logger.info(f"Supported languages: {settings.supported_languages_list}")

    try:
        # Initialize models
        await initialize_models()
        logger.info("Service started successfully!")
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down service...")


# Create FastAPI application
app = FastAPI(
    title="YouTube Transcription & Fact-Check Service",
    description="Speaker-diarized transcription and AI-powered fact-checking for YouTube videos",
    version="2.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(
    transcribe.router,
    prefix="/api",
    tags=["Transcription"]
)
app.include_router(
    jobs.router,
    prefix="/api",
    tags=["Jobs"]
)
app.include_router(
    fact_check.router,
    prefix="/api",
    tags=["Fact-Check"]
)

# Mount static files
static_path = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/index.html")
async def serve_index():
    """Serve the main HTML page."""
    index_path = os.path.join(static_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend not found"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,  # Set to True for development
        log_level=settings.LOG_LEVEL.lower()
    )
