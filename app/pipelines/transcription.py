"""
Audio transcription pipeline using faster-whisper.
"""
from typing import Dict, List, Optional
from faster_whisper import WhisperModel
# Need to import torch for device detection
import torch
from app.utils.logger import setup_logger
from app.core.config import settings

logger = setup_logger(__name__)


class Transcriber:
    """Handles audio transcription using faster-whisper."""

    def __init__(self, model_size: str = "base"):
        """
        Initialize the transcriber.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large-v2, large-v3)
        """
        self.model_size = model_size
        self.model = None

    def load_model(self):
        """Load the Whisper model."""
        if self.model is not None:
            logger.info("Whisper model already loaded")
            return

        try:
            logger.info(f"Loading Whisper model: {self.model_size}")

            # Determine device
            device = "cuda" if torch.cuda.is_available() else "cpu"
            compute_type = "float16" if device == "cuda" else "int8"

            logger.info(f"Using device: {device}, compute_type: {compute_type}")

            # Load model
            self.model = WhisperModel(
                self.model_size,
                device=device,
                compute_type=compute_type,
                download_root=settings.MODELS_DIR
            )

            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None
    ) -> Dict:
        """
        Transcribe audio file.

        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'en', 'th') or None for auto-detection

        Returns:
            Dictionary with transcription results including segments and detected language

        Raises:
            Exception: If transcription fails
        """
        if self.model is None:
            raise RuntimeError("Whisper model not loaded. Call load_model() first.")

        try:
            logger.info(f"Transcribing audio: {audio_path}")
            if language:
                logger.info(f"Using language: {language}")
            else:
                logger.info("Auto-detecting language")

            # Run transcription
            segments, info = self.model.transcribe(
                audio_path,
                language=language,
                beam_size=5,
                vad_filter=True,  # Voice activity detection
                vad_parameters=dict(
                    min_silence_duration_ms=500
                )
            )

            # Extract segments
            transcript_segments = []
            full_text = []

            for segment in segments:
                transcript_segments.append({
                    'start': segment.start,
                    'end': segment.end,
                    'text': segment.text.strip(),
                })
                full_text.append(segment.text.strip())

            detected_language = info.language
            language_probability = info.language_probability

            logger.info(
                f"Transcription complete. Language: {detected_language} "
                f"(probability: {language_probability:.2f})"
            )
            logger.info(f"Generated {len(transcript_segments)} transcript segments")

            return {
                'segments': transcript_segments,
                'language': detected_language,
                'language_probability': language_probability,
                'full_text': ' '.join(full_text)
            }

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise Exception(f"Audio transcription failed: {str(e)}")



# Global instance (will be initialized in model_loader)
transcriber: Transcriber = None


def get_transcriber() -> Transcriber:
    """Get the global transcriber instance with hardware-appropriate model size."""
    global transcriber
    if transcriber is None:
        # Detect device and select appropriate model size
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model_size = settings.get_whisper_model_size(device)
        logger.info(f"Initializing transcriber with model size '{model_size}' for device '{device}'")
        transcriber = Transcriber(model_size)
    return transcriber
