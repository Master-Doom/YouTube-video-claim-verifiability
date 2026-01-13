"""
Audio processing utility functions.
"""
from pydub import AudioSegment
from typing import Tuple
from app.utils.logger import setup_logger
from app.core.constants import AUDIO_SAMPLE_RATE, AUDIO_CHANNELS

logger = setup_logger(__name__)


def convert_to_wav(input_path: str, output_path: str, sample_rate: int = AUDIO_SAMPLE_RATE) -> str:
    """
    Convert audio file to WAV format with specified sample rate.

    Args:
        input_path: Path to input audio file
        output_path: Path to output WAV file
        sample_rate: Target sample rate in Hz

    Returns:
        Path to the output WAV file

    Raises:
        Exception: If conversion fails
    """
    try:
        logger.info(f"Converting {input_path} to WAV format")

        # Load audio file
        audio = AudioSegment.from_file(input_path)

        # Convert to mono
        if audio.channels > 1:
            audio = audio.set_channels(AUDIO_CHANNELS)
            logger.debug(f"Converted to mono ({AUDIO_CHANNELS} channel)")

        # Resample to target sample rate
        if audio.frame_rate != sample_rate:
            audio = audio.set_frame_rate(sample_rate)
            logger.debug(f"Resampled to {sample_rate} Hz")

        # Export as WAV
        audio.export(output_path, format="wav")
        logger.info(f"Successfully converted to WAV: {output_path}")

        return output_path
    except Exception as e:
        logger.error(f"Failed to convert audio to WAV: {e}")
        raise


def get_audio_duration(file_path: str) -> float:
    """
    Get the duration of an audio file in seconds.

    Args:
        file_path: Path to audio file

    Returns:
        Duration in seconds

    Raises:
        Exception: If unable to read audio file
    """
    try:
        audio = AudioSegment.from_file(file_path)
        duration = len(audio) / 1000.0  # Convert milliseconds to seconds
        logger.debug(f"Audio duration: {duration:.2f} seconds")
        return duration
    except Exception as e:
        logger.error(f"Failed to get audio duration: {e}")
        raise


def validate_audio_file(file_path: str) -> Tuple[bool, str]:
    """
    Validate an audio file.

    Args:
        file_path: Path to audio file

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        audio = AudioSegment.from_file(file_path)

        # Check if audio has content
        if len(audio) == 0:
            return False, "Audio file is empty"

        # Check minimum duration (1 second)
        if len(audio) < 1000:
            return False, "Audio file is too short (minimum 1 second)"

        return True, ""
    except Exception as e:
        return False, f"Invalid audio file: {str(e)}"


def format_timestamp(seconds: float) -> str:
    """
    Format seconds to HH:MM:SS.mmm timestamp.

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp string
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    else:
        return f"{minutes:02d}:{secs:06.3f}"


def get_audio_info(file_path: str) -> dict:
    """
    Get detailed information about an audio file.

    Args:
        file_path: Path to audio file

    Returns:
        Dictionary with audio information
    """
    try:
        audio = AudioSegment.from_file(file_path)

        return {
            "duration_seconds": len(audio) / 1000.0,
            "sample_rate": audio.frame_rate,
            "channels": audio.channels,
            "sample_width": audio.sample_width,
            "frame_count": audio.frame_count(),
            "duration_formatted": format_timestamp(len(audio) / 1000.0)
        }
    except Exception as e:
        logger.error(f"Failed to get audio info: {e}")
        raise
