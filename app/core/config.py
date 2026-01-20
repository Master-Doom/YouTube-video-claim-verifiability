"""
Configuration management using Pydantic Settings.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # HuggingFace Configuration
    HUGGINGFACE_TOKEN: str = Field(
        ...,
        description="HuggingFace API token for pyannote.audio models"
    )

    # Gemini API Configuration
    GEMINI_API_KEY: str = Field(
        default="",
        description="Google Gemini API key for fact-checking"
    )
    GEMINI_MODEL: str = Field(
        default="gemini-1.5-flash",
        description="Gemini model to use for claim extraction and verification"
    )
    GEMINI_REQUESTS_PER_MINUTE: int = Field(
        default=15,
        description="Gemini API rate limit (requests per minute)"
    )

    # Google Custom Search Configuration
    GOOGLE_SEARCH_API_KEY: str = Field(
        default="",
        description="Google Custom Search API key"
    )
    GOOGLE_SEARCH_CX: str = Field(
        default="",
        description="Google Custom Search Engine ID"
    )

    # Fact-Checking Configuration
    ENABLE_FACT_CHECKING: bool = Field(
        default=True,
        description="Enable fact-checking feature"
    )
    MAX_CLAIMS_TO_VERIFY: int = Field(
        default=10,
        description="Maximum number of claims to verify per video"
    )
    EVIDENCE_SOURCES_PER_CLAIM: int = Field(
        default=5,
        description="Number of evidence sources to fetch per claim"
    )

    # YouTube Configuration
    YOUTUBE_COOKIES_PATH: str = Field(
        default="",
        description="Path to YouTube cookies.txt file for authentication (bypasses bot detection)"
    )

    # Directory Configuration
    TEMP_DIR: str = Field(
        default="./temp",
        description="Directory for temporary audio files"
    )
    MODELS_DIR: str = Field(
        default="./models",
        description="Directory for cached models"
    )

    # Model Configuration - Hardware-Specific
    WHISPER_MODEL_SIZE_GPU: str = Field(
        default="medium",
        description="Whisper model for GPU deployment (medium recommended for Thai accuracy)"
    )
    WHISPER_MODEL_SIZE_CPU: str = Field(
        default="small",
        description="Whisper model for CPU deployment (small for balanced speed/accuracy)"
    )
    WHISPER_MODEL_SIZE: str = Field(
        default="",
        description="Manual override - if set, ignores auto-detection and uses this size"
    )

    # Processing Limits
    MAX_VIDEO_LENGTH_MINUTES: int = Field(
        default=120,
        description="Maximum video length in minutes"
    )

    # Supported Languages
    SUPPORTED_LANGUAGES: str = Field(
        default="en,th",
        description="Comma-separated list of supported language codes"
    )

    # Server Configuration
    HOST: str = Field(default="0.0.0.0", description="Server host")
    PORT: int = Field(default=8000, description="Server port")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def supported_languages_list(self) -> List[str]:
        """Get supported languages as a list."""
        return [lang.strip() for lang in self.SUPPORTED_LANGUAGES.split(",")]

    @property
    def max_video_length_seconds(self) -> int:
        """Get max video length in seconds."""
        return self.MAX_VIDEO_LENGTH_MINUTES * 60

    def ensure_directories(self):
        """Ensure required directories exist."""
        Path(self.TEMP_DIR).mkdir(parents=True, exist_ok=True)
        Path(self.MODELS_DIR).mkdir(parents=True, exist_ok=True)

    def get_whisper_model_size(self, device: str) -> str:
        """
        Get the appropriate Whisper model size based on device.

        Args:
            device: The detected device ("cuda" or "cpu")

        Returns:
            Model size string (e.g., "small", "medium")
        """
        # If manual override is set, use it
        if self.WHISPER_MODEL_SIZE:
            return self.WHISPER_MODEL_SIZE

        # Otherwise, select based on hardware
        if device == "cuda":
            return self.WHISPER_MODEL_SIZE_GPU
        else:
            return self.WHISPER_MODEL_SIZE_CPU


# Global settings instance
settings = Settings()
