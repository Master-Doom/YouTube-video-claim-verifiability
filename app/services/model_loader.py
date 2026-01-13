"""
Model loader service for initializing and caching ML models.
"""
from typing import Optional
from app.pipelines.diarization import SpeakerDiarizer, get_diarizer
from app.pipelines.transcription import Transcriber, get_transcriber
from app.utils.logger import setup_logger
from app.core.config import settings

logger = setup_logger(__name__)


class ModelLoader:
    """Service for loading and managing ML models."""

    def __init__(self):
        """Initialize the model loader."""
        self.whisper_loaded = False
        self.diarization_loaded = False
        self.transcriber: Optional[Transcriber] = None
        self.diarizer: Optional[SpeakerDiarizer] = None

    async def load_all_models(self):
        """Load all required models at startup."""
        logger.info("Starting model loading process...")

        try:
            # Ensure directories exist
            settings.ensure_directories()

            # Load Whisper model
            await self.load_whisper_model()

            # Load diarization model
            await self.load_diarization_model()

            logger.info("All models loaded successfully!")

        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            raise

    async def load_whisper_model(self):
        """Load the Whisper transcription model."""
        if self.whisper_loaded:
            logger.info("Whisper model already loaded")
            return

        try:
            logger.info("Loading Whisper model...")
            self.transcriber = get_transcriber()
            self.transcriber.load_model()
            self.whisper_loaded = True
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise

    async def load_diarization_model(self):
        """Load the speaker diarization model."""
        if self.diarization_loaded:
            logger.info("Diarization model already loaded")
            return

        try:
            logger.info("Loading diarization model...")
            self.diarizer = get_diarizer()
            self.diarizer.load_model()
            self.diarization_loaded = True
            logger.info("Diarization model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load diarization model: {e}")
            raise

    def get_model_status(self) -> dict:
        """
        Get the current status of loaded models.

        Returns:
            Dictionary with model status information
        """
        return {
            'whisper_loaded': self.whisper_loaded,
            'whisper_model_size': settings.WHISPER_MODEL_SIZE if self.whisper_loaded else None,
            'diarization_loaded': self.diarization_loaded,
            'models_loaded': self.whisper_loaded and self.diarization_loaded
        }

    def is_ready(self) -> bool:
        """
        Check if all models are loaded and ready.

        Returns:
            True if all models are loaded, False otherwise
        """
        return self.whisper_loaded and self.diarization_loaded


# Global instance
model_loader = ModelLoader()


async def initialize_models():
    """Initialize all models at application startup."""
    await model_loader.load_all_models()


def get_model_status() -> dict:
    """Get the current model status."""
    return model_loader.get_model_status()


def is_service_ready() -> bool:
    """Check if the service is ready to process requests."""
    return model_loader.is_ready()
