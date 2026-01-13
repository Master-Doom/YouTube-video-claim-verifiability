"""
FastAPI dependencies.
"""
from fastapi import HTTPException, status
from app.services.model_loader import is_service_ready
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


async def check_service_ready():
    """
    Dependency to check if the service is ready to process requests.

    Raises:
        HTTPException: If the service is not ready
    """
    if not is_service_ready():
        logger.error("Service not ready - models not loaded")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is still initializing. Please try again in a moment."
        )
