"""
Fact-checking API endpoint.
"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException

from app.models.schemas import FactCheckRequest, ErrorResponse
from app.pipelines.orchestrator import process_youtube_video
from app.pipelines.fact_checking import fact_checker
from app.api.dependencies import check_service_ready
from app.services.job_manager import job_manager
from app.services.gemini_service import gemini_service
from app.utils.logger import setup_logger
from app.core.config import settings

logger = setup_logger(__name__)

router = APIRouter()


@router.post(
    "/transcribe-and-fact-check",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    }
)
async def transcribe_and_fact_check(
    request: FactCheckRequest,
    _: None = Depends(check_service_ready)
):
    """
    Submit a YouTube video for transcription AND fact-checking.

    This endpoint performs:
    1. Video download and audio extraction
    2. Speaker diarization
    3. Transcription
    4. Factual claim extraction
    5. Evidence retrieval
    6. Claim verification

    Returns immediately with a job_id. Poll GET /api/jobs/{job_id} for results.

    Args:
        request: FactCheckRequest with youtube_url, language, and optional max_claims

    Returns:
        Job ID and initial status
    """
    # Check if fact-checking is enabled
    if not settings.ENABLE_FACT_CHECKING:
        raise HTTPException(
            status_code=503,
            detail="Fact-checking is disabled on this server"
        )

    # Check if Gemini is configured
    if not gemini_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Fact-checking requires Gemini API key. Please configure GEMINI_API_KEY."
        )

    logger.info(f"📋 Received fact-check request for URL: {request.youtube_url}")

    # Create job with fact_check flag
    job_id = job_manager.create_job(
        youtube_url=request.youtube_url,
        language=request.language,
        fact_check=True
    )

    # Start processing in background
    asyncio.create_task(
        process_fact_check_job(job_id, request.max_claims)
    )

    return {
        "job_id": job_id,
        "status": "pending",
        "fact_check": True,
        "message": "Job submitted. Poll GET /api/jobs/{job_id} for status and results."
    }


async def process_fact_check_job(job_id: str, max_claims: int = None):
    """
    Background task to process a fact-checking job.

    Args:
        job_id: The job ID to process
        max_claims: Maximum claims to verify (optional)
    """
    job = job_manager.get_job(job_id)
    if not job:
        logger.error(f"Job {job_id} not found")
        return

    try:
        # Mark as processing
        job_manager.set_processing(job_id)

        # =========================================================
        # Phase 1: Transcription
        # =========================================================
        job_manager.update_progress(
            job_id,
            "Phase 1/2: Downloading and transcribing video...",
            phase="transcription"
        )

        logger.info(f"📥 Phase 1: Transcribing video for job {job_id}")

        result = await process_youtube_video(
            youtube_url=job.youtube_url,
            language=job.language
        )

        # Convert segments to list format
        segments = [
            {
                "speaker": seg['speaker'],
                "start": seg['start'],
                "end": seg['end'],
                "text": seg['text']
            }
            for seg in result['segments']
        ]

        logger.info(
            f"✅ Transcription complete: {result['video_title']} "
            f"({len(segments)} segments, {result['total_speakers']} speakers)"
        )

        # =========================================================
        # Phase 2: Fact-Checking
        # =========================================================
        job_manager.update_progress(
            job_id,
            "Phase 2/2: Analyzing and fact-checking claims...",
            phase="fact_checking"
        )

        logger.info(f"🔍 Phase 2: Fact-checking for job {job_id}")

        # Progress callback for detailed updates
        def fact_check_progress(msg: str):
            job_manager.update_progress(job_id, f"Phase 2/2: {msg}", phase="fact_checking")

        fact_check_result = await fact_checker.run_fact_check(
            segments=segments,
            progress_callback=fact_check_progress,
            max_claims=max_claims
        )

        # =========================================================
        # Combine Results
        # =========================================================
        response_data = {
            "video_title": result['video_title'],
            "duration": result['duration'],
            "language": result['language'],
            "segments": segments,
            "total_speakers": result['total_speakers'],
            "fact_check": fact_check_result,
            "disclaimer": fact_check_result.get('disclaimer', '')
        }

        job_manager.complete_job(job_id, response_data)

        claims_found = fact_check_result.get('claims_found', 0)
        summary = fact_check_result.get('summary', {})
        logger.info(
            f"✅ Fact-check job {job_id} completed: "
            f"{claims_found} claims found, "
            f"{summary.get('supported', 0)} supported, "
            f"{summary.get('refuted', 0)} refuted, "
            f"{summary.get('inconclusive', 0)} inconclusive"
        )

    except ValueError as e:
        logger.error(f"Validation error for job {job_id}: {e}")
        job_manager.fail_job(job_id, str(e))

    except Exception as e:
        logger.error(f"Processing error for job {job_id}: {e}", exc_info=True)
        job_manager.fail_job(job_id, str(e))


@router.get("/fact-check-status")
async def fact_check_status():
    """
    Check the status and availability of fact-checking services.

    Returns:
        Status of Gemini API and SerpAPI
    """
    from app.services.web_search_service import web_search_service

    return {
        "fact_checking_enabled": settings.ENABLE_FACT_CHECKING,
        "gemini_configured": gemini_service.is_configured(),
        "gemini_model": settings.GEMINI_MODEL,
        "web_search_configured": web_search_service.is_configured(),
        "search_provider": "serpapi",
        "max_claims_to_verify": settings.MAX_CLAIMS_TO_VERIFY,
        "evidence_sources_per_claim": settings.EVIDENCE_SOURCES_PER_CLAIM
    }
