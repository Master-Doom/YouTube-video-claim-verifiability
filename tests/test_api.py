"""
Basic tests for the YouTube Transcription Service API.
"""
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    """Test the health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "models_loaded" in data


@pytest.mark.asyncio
async def test_root_endpoint():
    """Test the root endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "endpoints" in data


@pytest.mark.asyncio
async def test_transcribe_invalid_url():
    """Test transcription with an invalid URL."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/transcribe",
            json={"youtube_url": "https://not-a-youtube-url.com"}
        )
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_transcribe_invalid_language():
    """Test transcription with an invalid language."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/transcribe",
            json={
                "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "language": "invalid"
            }
        )
        assert response.status_code == 422  # Validation error
