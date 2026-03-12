"""
Pydantic models for API requests and responses.
"""
from typing import List, Optional, Dict, Any, Literal
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


# =============================================================================
# Fact-Checking Schemas
# =============================================================================

class EvidenceSource(BaseModel):
    """Model for an evidence source used in verification."""

    source_url: str = Field(
        ...,
        description="URL of the evidence source"
    )
    source_title: Optional[str] = Field(
        default=None,
        description="Title of the source"
    )
    quote: str = Field(
        ...,
        description="Relevant quote or excerpt from the source"
    )
    reliability: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Source reliability score (0-1)"
    )


class ClaimData(BaseModel):
    """Model for an extracted claim."""

    claim_text: str = Field(
        ...,
        description="The factual claim text"
    )
    speaker: str = Field(
        default="UNKNOWN",
        description="Speaker who made the claim"
    )
    start_time: float = Field(
        default=0.0,
        ge=0.0,
        description="Start timestamp in seconds"
    )
    end_time: float = Field(
        default=0.0,
        ge=0.0,
        description="End timestamp in seconds"
    )
    claim_type: str = Field(
        default="scientific",
        description="Type of claim (scientific -- this system focuses on scientific claims only)"
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Extraction confidence score"
    )
    search_query: Optional[str] = Field(
        default=None,
        description="Suggested search query"
    )
    key_entities: List[str] = Field(
        default_factory=list,
        description="Key entities mentioned in the claim"
    )


class ClaimVerification(BaseModel):
    """Model for a verified claim with verdict and evidence."""

    claim: ClaimData = Field(
        ...,
        description="The claim that was verified"
    )
    verdict: Literal["supported", "refuted", "inconclusive", "error"] = Field(
        ...,
        description="Verification verdict"
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Confidence in the verdict (0-1)"
    )
    explanation: str = Field(
        default="",
        description="Explanation of the verdict"
    )
    supporting_evidence: List[EvidenceSource] = Field(
        default_factory=list,
        description="Evidence supporting the claim"
    )
    counter_evidence: List[EvidenceSource] = Field(
        default_factory=list,
        description="Evidence contradicting the claim"
    )
    key_finding: Optional[str] = Field(
        default=None,
        description="Most important finding"
    )
    caveats: Optional[str] = Field(
        default=None,
        description="Important limitations or caveats"
    )


class FactCheckSummary(BaseModel):
    """Summary statistics for fact-checking results."""

    supported: int = Field(default=0, description="Number of supported claims")
    refuted: int = Field(default=0, description="Number of refuted claims")
    inconclusive: int = Field(default=0, description="Number of inconclusive claims")
    error: int = Field(default=0, description="Number of claims with errors")
    total: int = Field(default=0, description="Total claims verified")
    average_confidence: float = Field(default=0.0, description="Average confidence score")
    supported_pct: float = Field(default=0.0, description="Percentage of supported claims")
    refuted_pct: float = Field(default=0.0, description="Percentage of refuted claims")
    inconclusive_pct: float = Field(default=0.0, description="Percentage of inconclusive claims")


class FactCheckRequest(BaseModel):
    """Request model for fact-checking endpoint."""

    youtube_url: str = Field(
        ...,
        description="YouTube video URL",
        examples=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"]
    )
    language: Optional[str] = Field(
        default=None,
        description="Language code (en, th) or None for auto-detection"
    )
    max_claims: Optional[int] = Field(
        default=None,
        ge=1,
        le=50,
        description="Maximum number of claims to verify"
    )

    @field_validator("youtube_url")
    @classmethod
    def validate_youtube_url(cls, v: str) -> str:
        """Validate that the URL is a valid YouTube URL."""
        youtube_regex = r"^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$"
        if not re.match(youtube_regex, v):
            raise ValueError("Invalid YouTube URL format")
        return v


class FactCheckResult(BaseModel):
    """Fact-checking results container."""

    claims_found: int = Field(
        default=0,
        description="Number of claims extracted"
    )
    claims_verified: int = Field(
        default=0,
        description="Number of claims verified"
    )
    verifications: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of claim verifications"
    )
    summary: FactCheckSummary = Field(
        default_factory=FactCheckSummary,
        description="Summary statistics"
    )
    disclaimer: str = Field(
        default="",
        description="Disclaimer text"
    )
    processing_time_seconds: float = Field(
        default=0.0,
        description="Total processing time"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if fact-checking failed"
    )
    message: Optional[str] = Field(
        default=None,
        description="Informational message"
    )


class FactCheckResponse(BaseModel):
    """Combined response for transcription + fact-checking."""

    video_title: str = Field(
        ...,
        description="Title of the YouTube video"
    )
    duration: float = Field(
        ...,
        ge=0.0,
        description="Video duration in seconds"
    )
    language: str = Field(
        ...,
        description="Detected or specified language"
    )
    segments: List[SpeakerSegment] = Field(
        ...,
        description="Transcript segments with speaker labels"
    )
    total_speakers: int = Field(
        ...,
        ge=1,
        description="Number of unique speakers"
    )
    fact_check: FactCheckResult = Field(
        ...,
        description="Fact-checking results"
    )
    disclaimer: str = Field(
        default="",
        description="Overall disclaimer"
    )
