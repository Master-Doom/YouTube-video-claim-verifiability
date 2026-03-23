"""
Health check endpoint.
"""
from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from app.models.schemas import HealthResponse
from app.services.model_loader import get_model_status
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify service status.

    Returns:
        HealthResponse with service status and model information
    """
    status = get_model_status()

    return HealthResponse(
        status="healthy" if status['models_loaded'] else "initializing",
        models_loaded=status['models_loaded'],
        whisper_model=status['whisper_model_size'],
        diarization_available=status['diarization_loaded']
    )


@router.get("/")
async def root():
    """Redirect root to the frontend UI."""
    return RedirectResponse(url="/index.html")
