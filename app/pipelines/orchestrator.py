"""
Pipeline orchestrator that coordinates all processing steps.
"""
from typing import Dict, Optional
from app.pipelines.audio_extraction import audio_extractor
from app.pipelines.diarization import get_diarizer
from app.pipelines.transcription import get_transcriber
from app.pipelines.alignment import align_speakers_with_transcript, get_speaker_statistics
from app.utils.logger import setup_logger
from app.utils.file_utils import cleanup_temp_file
from app.core.constants import ERROR_PROCESSING_FAILED

logger = setup_logger(__name__)


class PipelineOrchestrator:
    """Orchestrates the complete video processing pipeline."""

    def __init__(self):
        """Initialize the orchestrator."""
        self.audio_extractor = audio_extractor
        self.diarizer = get_diarizer()
        self.transcriber = get_transcriber()

    async def process_video(
        self,
        youtube_url: str,
        language: Optional[str] = None
    ) -> Dict:
        """
        Process a YouTube video through the complete pipeline.

        Pipeline steps:
        1. Download and extract audio
        2. Perform speaker diarization
        3. Transcribe audio
        4. Align speakers with transcript
        5. Cleanup temporary files

        Args:
            youtube_url: YouTube video URL
            language: Optional language code for transcription

        Returns:
            Dictionary with processing results

        Raises:
            Exception: If any step in the pipeline fails
        """
        audio_path = None

        try:
            logger.info(f"Starting pipeline for URL: {youtube_url}")

            # Step 1: Download and extract audio
            logger.info("Step 1/4: Extracting audio from YouTube video")
            audio_path, metadata = self.audio_extractor.download_and_extract(youtube_url)

            # Step 2: Perform speaker diarization
            logger.info("Step 2/4: Performing speaker diarization")
            diarization_segments = self.diarizer.run_diarization(audio_path)

            # Step 3: Transcribe audio
            logger.info("Step 3/4: Transcribing audio")
            transcription_result = self.transcriber.transcribe(
                audio_path,
                language=language
            )

            # Step 4: Align speakers with transcript
            logger.info("Step 4/4: Aligning speakers with transcript")
            aligned_segments = align_speakers_with_transcript(
                diarization_segments,
                transcription_result['segments']
            )

            # Get speaker statistics
            speaker_stats = get_speaker_statistics(aligned_segments)

            # Prepare final result
            result = {
                'video_title': metadata['title'],
                'duration': metadata['duration'],
                'language': transcription_result['language'],
                'language_probability': transcription_result['language_probability'],
                'segments': aligned_segments,
                'total_speakers': speaker_stats['total_speakers'],
                'speaker_statistics': speaker_stats['speakers'],
                'metadata': metadata
            }

            logger.info("Pipeline completed successfully")
            logger.info(f"Total segments: {len(aligned_segments)}")
            logger.info(f"Total speakers: {speaker_stats['total_speakers']}")

            return result

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise Exception(f"{ERROR_PROCESSING_FAILED}: {str(e)}")

        finally:
            # Cleanup temporary audio file
            if audio_path:
                logger.info("Cleaning up temporary files")
                cleanup_temp_file(audio_path)


# Global instance
orchestrator = PipelineOrchestrator()


async def process_youtube_video(
    youtube_url: str,
    language: Optional[str] = None
) -> Dict:
    """
    Convenience function to process a YouTube video.

    Args:
        youtube_url: YouTube video URL
        language: Optional language code

    Returns:
        Processing results dictionary
    """
    return await orchestrator.process_video(youtube_url, language)
