"""
Job status API endpoint.
"""
from fastapi import APIRouter, HTTPException
from app.services.job_manager import job_manager
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

router = APIRouter()


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Get the status of a transcription job.

    Args:
        job_id: The job ID returned from POST /api/transcribe

    Returns:
        Job status, progress, and results (if completed)
    """
    job = job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job.to_dict()
