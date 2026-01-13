"""
Pydantic models for API requests and responses.
"""
from typing import List, Optional
from pydantic import BaseModel, Field, HttpUrl, field_validator
import re


class TranscribeRequest(BaseModel):
    """Request model for transcription endpoint."""

    youtube_url: str = Field(
        ...,
        description="YouTube video URL",
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
    )
    language: Optional[str] = Field(
        default=None,
        description="Language code (en, th) or None for auto-detection",
        examples=["en", "th", None]
    )

    @field_validator("youtube_url")
    @classmethod
    def validate_youtube_url(cls, v: str) -> str:
        """Validate that the URL is a valid YouTube URL."""
        youtube_regex = r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$"
        if not re.match(youtube_regex, v):
            raise ValueError("Invalid YouTube URL format")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: Optional[str]) -> Optional[str]:
        """Validate language code."""
        if v is not None and v not in ["en", "th", "auto"]:
            raise ValueError("Language must be 'en', 'th', or None for auto-detection")
        return v


class SpeakerSegment(BaseModel):
    """Model for a speaker segment with transcription."""

    speaker: str = Field(
        ...,
        description="Speaker identifier (e.g., 'SPEAKER_00')",
        examples=["SPEAKER_00"]
    )
    start: float = Field(
        ...,
        description="Start time in seconds",
        ge=0.0,
        examples=[0.0]
    )
    end: float = Field(
        ...,
        description="End time in seconds",
        gt=0.0,
        examples=[5.5]
    )
    text: str = Field(
        ...,
        description="Transcribed text for this segment",
        examples=["Hello, how are you?"]
    )

    @field_validator("end")
    @classmethod
    def validate_end_time(cls, v: float, info) -> float:
        """Ensure end time is after start time."""
        if "start" in info.data and v <= info.data["start"]:
            raise ValueError("End time must be greater than start time")
        return v


class TranscribeResponse(BaseModel):
    """Response model for transcription endpoint."""

    video_title: str = Field(
        ...,
        description="Title of the YouTube video",
        examples=["Sample Video Title"]
    )
    duration: float = Field(
        ...,
        description="Video duration in seconds",
        ge=0.0,
        examples=[300.5]
    )
    language: str = Field(
        ...,
        description="Detected or specified language code",
        examples=["en"]
    )
    segments: List[SpeakerSegment] = Field(
        ...,
        description="List of speaker segments with transcriptions"
    )
    total_speakers: int = Field(
        ...,
        description="Total number of unique speakers detected",
        ge=1,
        examples=[2]
    )


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(
        default="healthy",
        description="Service status",
        examples=["healthy"]
    )
    models_loaded: bool = Field(
        ...,
        description="Whether required models are loaded",
        examples=[True]
    )
    whisper_model: Optional[str] = Field(
        default=None,
        description="Loaded Whisper model size",
        examples=["base"]
    )
    diarization_available: bool = Field(
        ...,
        description="Whether diarization model is available",
        examples=[True]
    )


class ErrorResponse(BaseModel):
    """Response model for error responses."""

    detail: str = Field(
        ...,
        description="Error message",
        examples=["An error occurred"]
    )
    error_code: Optional[str] = Field(
        default=None,
        description="Machine-readable error code",
        examples=["INVALID_URL"]
    )
