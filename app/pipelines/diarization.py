"""
Speaker diarization pipeline using pyannote.audio.
"""
from typing import List, Dict
from pyannote.audio import Pipeline
import torch
from app.utils.logger import setup_logger
from app.core.config import settings
from app.core.constants import DIARIZATION_MODEL

logger = setup_logger(__name__)


class SpeakerDiarizer:
    """Handles speaker diarization using pyannote.audio."""

    def __init__(self, hf_token: str):
        """
        Initialize the speaker diarizer.

        Args:
            hf_token: HuggingFace API token
        """
        self.hf_token = hf_token
        self.pipeline = None

    def load_model(self):
        """Load the diarization model."""
        if self.pipeline is not None:
            logger.info("Diarization model already loaded")
            return

        try:
            logger.info(f"Loading diarization model: {DIARIZATION_MODEL}")

            # Determine device
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            logger.info(f"Using device: {device}")

            # Load pipeline
            self.pipeline = Pipeline.from_pretrained(
                DIARIZATION_MODEL,
                use_auth_token=self.hf_token
            )

            # Move to device
            self.pipeline = self.pipeline.to(device)

            logger.info("Diarization model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load diarization model: {e}")
            raise

    def run_diarization(self, audio_path: str) -> List[Dict]:
        """
        Perform speaker diarization on audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            List of diarization segments with speaker labels and timestamps

        Raises:
            Exception: If diarization fails
        """
        if self.pipeline is None:
            raise RuntimeError("Diarization model not loaded. Call load_model() first.")

        try:
            logger.info(f"Running speaker diarization on: {audio_path}")

            # Run diarization
            diarization = self.pipeline(audio_path)

            # Extract segments
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segment = {
                    'speaker': speaker,
                    'start': turn.start,
                    'end': turn.end,
                }
                segments.append(segment)

            logger.info(f"Diarization complete. Found {len(segments)} segments")

            # Log speaker statistics
            speakers = set(seg['speaker'] for seg in segments)
            logger.info(f"Detected {len(speakers)} unique speakers: {', '.join(sorted(speakers))}")

            return segments

        except Exception as e:
            logger.error(f"Diarization failed: {e}")
            raise Exception(f"Speaker diarization failed: {str(e)}")


# Global instance (will be initialized in model_loader)
speaker_diarizer: SpeakerDiarizer = None


def get_diarizer() -> SpeakerDiarizer:
    """Get the global diarizer instance."""
    global speaker_diarizer
    if speaker_diarizer is None:
        speaker_diarizer = SpeakerDiarizer(settings.HUGGINGFACE_TOKEN)
    return speaker_diarizer
