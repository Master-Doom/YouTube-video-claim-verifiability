"""
Transcription API endpoint.
"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.schemas import TranscribeRequest, TranscribeResponse, SpeakerSegment, ErrorResponse
from app.pipelines.orchestrator import process_youtube_video
from app.api.dependencies import check_service_ready
from app.services.job_manager import job_manager, JobStatus
from app.utils.logger import setup_logger
from app.core.constants import ERROR_INVALID_URL, ERROR_PROCESSING_FAILED

logger = setup_logger(__name__)

router = APIRouter()


@router.post(
    "/transcribe",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    }
)
async def transcribe_video(
    request: TranscribeRequest,
    _: None = Depends(check_service_ready)
):
    """
    Submit a YouTube video for transcription with speaker diarization.

    This endpoint returns immediately with a job_id. Use GET /api/jobs/{job_id}
    to poll for status and results.

    Args:
        request: TranscribeRequest containing youtube_url and optional language

    Returns:
        Job ID and initial status
    """
    logger.info(f"Received transcription request for URL: {request.youtube_url}")

    # Create job
    job_id = job_manager.create_job(request.youtube_url, request.language)

    # Start processing in background
    asyncio.create_task(process_transcription_job(job_id))

    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Job submitted. Poll GET /api/jobs/{job_id} for status."
    }


async def process_transcription_job(job_id: str):
    """
    Background task to process a transcription job.

    Args:
        job_id: The job ID to process
    """
    job = job_manager.get_job(job_id)
    if not job:
        logger.error(f"Job {job_id} not found")
        return

    try:
        # Mark as processing
        job_manager.set_processing(job_id)
        job_manager.update_progress(job_id, "Downloading and extracting audio...")

        # Process the video
        result = await process_youtube_video(
            youtube_url=job.youtube_url,
            language=job.language
        )

        # Convert to response format
        segments = [
            {
                "speaker": seg['speaker'],
                "start": seg['start'],
                "end": seg['end'],
                "text": seg['text']
            }
            for seg in result['segments']
        ]

        response_data = {
            "video_title": result['video_title'],
            "duration": result['duration'],
            "language": result['language'],
            "segments": segments,
            "total_speakers": result['total_speakers']
        }

        job_manager.complete_job(job_id, response_data)

        logger.info(
            f"Successfully processed video: {result['video_title']} "
            f"({len(segments)} segments, {result['total_speakers']} speakers)"
        )

    except ValueError as e:
        logger.error(f"Validation error for job {job_id}: {e}")
        job_manager.fail_job(job_id, str(e))

    except Exception as e:
        logger.error(f"Processing error for job {job_id}: {e}")
        job_manager.fail_job(job_id, str(e))
