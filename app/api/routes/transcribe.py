"""
Transcription API endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.schemas import TranscribeRequest, TranscribeResponse, SpeakerSegment, ErrorResponse
from app.pipelines.orchestrator import process_youtube_video
from app.api.dependencies import check_service_ready
from app.utils.logger import setup_logger
from app.core.constants import ERROR_INVALID_URL, ERROR_PROCESSING_FAILED

logger = setup_logger(__name__)

router = APIRouter()


@router.post(
    "/transcribe",
    response_model=TranscribeResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
        500: {"model": ErrorResponse, "description": "Processing failed"}
    }
)
async def transcribe_video(
    request: TranscribeRequest,
    _: None = Depends(check_service_ready)
):
    """
    Transcribe a YouTube video with speaker diarization.

    This endpoint:
    1. Downloads audio from the provided YouTube URL
    2. Performs speaker diarization to identify different speakers
    3. Transcribes the audio with language detection
    4. Aligns speaker labels with transcript segments

    Args:
        request: TranscribeRequest containing youtube_url and optional language

    Returns:
        TranscribeResponse with video metadata and speaker-labeled transcript segments

    Raises:
        HTTPException: If validation fails or processing encounters an error
    """
    try:
        logger.info(f"Received transcription request for URL: {request.youtube_url}")

        # Process the video
        result = await process_youtube_video(
            youtube_url=request.youtube_url,
            language=request.language
        )

        # Convert segments to response model
        segments = [
            SpeakerSegment(
                speaker=seg['speaker'],
                start=seg['start'],
                end=seg['end'],
                text=seg['text']
            )
            for seg in result['segments']
        ]

        response = TranscribeResponse(
            video_title=result['video_title'],
            duration=result['duration'],
            language=result['language'],
            segments=segments,
            total_speakers=result['total_speakers']
        )

        logger.info(
            f"Successfully processed video: {result['video_title']} "
            f"({len(segments)} segments, {result['total_speakers']} speakers)"
        )

        return response

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Processing error: {e}")

        # Determine appropriate error code
        error_message = str(e)
        if ERROR_INVALID_URL in error_message:
            status_code = status.HTTP_400_BAD_REQUEST
        elif "duration exceeds" in error_message.lower():
            status_code = status.HTTP_400_BAD_REQUEST
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        raise HTTPException(
            status_code=status_code,
            detail=error_message
        )
