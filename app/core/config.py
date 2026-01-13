"""
Configuration management using Pydantic Settings.
"""
from typing import List
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

    # Directory Configuration
    TEMP_DIR: str = Field(
        default="./temp",
        description="Directory for temporary audio files"
    )
    MODELS_DIR: str = Field(
        default="./models",
        description="Directory for cached models"
    )

    # Model Configuration
    WHISPER_MODEL_SIZE: str = Field(
        default="base",
        description="Whisper model size (tiny, base, small, medium, large-v2, large-v3)"
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


# Global settings instance
settings = Settings()
