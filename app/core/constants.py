"""
Application constants.
"""

# Audio Processing Constants
AUDIO_SAMPLE_RATE = 16000  # Hz - Required for Whisper
AUDIO_CHANNELS = 1  # Mono
AUDIO_FORMAT = "wav"

# Language Codes
LANGUAGE_CODES = {
    "en": "English",
    "th": "Thai",
    "auto": "Auto-detect"
}

# Model Names
WHISPER_MODELS = [
    "tiny",
    "base",
    "small",
    "medium",
    "large-v2",
    "large-v3"
]

DIARIZATION_MODEL = "pyannote/speaker-diarization-3.1"
SEGMENTATION_MODEL = "pyannote/segmentation-3.0"

# Processing Constraints
MIN_SEGMENT_DURATION = 0.1  # seconds
MAX_SPEAKERS = 10  # Maximum number of speakers to detect

# API Response Messages
ERROR_INVALID_URL = "Invalid YouTube URL provided"
ERROR_VIDEO_TOO_LONG = "Video duration exceeds maximum allowed length"
ERROR_DOWNLOAD_FAILED = "Failed to download video"
ERROR_PROCESSING_FAILED = "Failed to process video"
ERROR_MISSING_TOKEN = "HuggingFace token not configured"

# File Patterns
ALLOWED_AUDIO_EXTENSIONS = [".wav", ".mp3", ".m4a", ".flac"]
TEMP_FILE_PREFIX = "yt_audio_"
