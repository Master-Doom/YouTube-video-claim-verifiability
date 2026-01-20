"""
Gemini API service for LLM-based claim extraction and verification.
"""
import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from app.utils.logger import setup_logger
from app.core.config import settings

logger = setup_logger(__name__)


class GeminiRateLimiter:
    """Token bucket rate limiter for Gemini API."""

    def __init__(self, requests_per_minute: int = 15):
        self.requests_per_minute = requests_per_minute
        self.request_times: List[datetime] = []
        self._lock = asyncio.Lock()

    async def wait_if_needed(self):
        """Wait if rate limit would be exceeded."""
        async with self._lock:
            now = datetime.utcnow()
            minute_ago = now - timedelta(minutes=1)

            # Remove timestamps older than 1 minute
            self.request_times = [t for t in self.request_times if t > minute_ago]

            if len(self.request_times) >= self.requests_per_minute:
                # Calculate wait time based on oldest request
                oldest = min(self.request_times)
                wait_seconds = (oldest + timedelta(minutes=1) - now).total_seconds()
                if wait_seconds > 0:
                    logger.info(f"⏳ Rate limit reached, waiting {wait_seconds:.1f}s")
                    await asyncio.sleep(wait_seconds + 0.5)

            self.request_times.append(datetime.utcnow())


class GeminiService:
    """Service for interacting with Google Gemini API."""

    def __init__(self):
        self.model = None
        self.rate_limiter = GeminiRateLimiter(settings.GEMINI_REQUESTS_PER_MINUTE)
        self._initialized = False

    def initialize(self):
        """Initialize the Gemini client."""
        if self._initialized:
            return

        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured")

        genai.configure(api_key=settings.GEMINI_API_KEY)

        # Configure safety settings to be less restrictive for fact-checking
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        }

        self.model = genai.GenerativeModel(
            settings.GEMINI_MODEL,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.1,  # Low temperature for consistent outputs
            ),
            safety_settings=safety_settings,
        )

        self._initialized = True
        logger.info(f"✅ Gemini service initialized with model: {settings.GEMINI_MODEL}")

    async def generate_json(
        self,
        prompt: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Generate JSON response from Gemini with rate limiting and retries.

        Args:
            prompt: The prompt to send to Gemini
            max_retries: Maximum number of retry attempts

        Returns:
            Parsed JSON response as a dictionary
        """
        self.initialize()

        for attempt in range(max_retries):
            try:
                await self.rate_limiter.wait_if_needed()

                logger.debug(f"🤖 Sending request to Gemini (attempt {attempt + 1})")

                # Run synchronous API call in thread pool
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt
                )

                # Check for blocked response
                if not response.text:
                    logger.warning("Gemini returned empty response")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    return {"error": "Empty response from Gemini"}

                # Parse JSON response
                try:
                    result = json.loads(response.text)
                    logger.debug("✅ Gemini response parsed successfully")
                    return result
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parse error: {e}")
                    # Try to extract JSON from response
                    text = response.text.strip()
                    if text.startswith("```json"):
                        text = text[7:]
                    if text.startswith("```"):
                        text = text[3:]
                    if text.endswith("```"):
                        text = text[:-3]
                    return json.loads(text.strip())

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Gemini response as JSON: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return {"error": f"JSON parse error: {str(e)}"}

            except Exception as e:
                logger.warning(f"Gemini API error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Gemini API failed after {max_retries} attempts: {e}")
                    return {"error": str(e)}

        return {"error": "Max retries exceeded"}

    async def generate_text(
        self,
        prompt: str,
        max_retries: int = 3
    ) -> str:
        """
        Generate plain text response from Gemini.

        Args:
            prompt: The prompt to send to Gemini
            max_retries: Maximum number of retry attempts

        Returns:
            Text response
        """
        self.initialize()

        # Use a model without JSON constraint for text generation
        text_model = genai.GenerativeModel(
            settings.GEMINI_MODEL,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
            ),
        )

        for attempt in range(max_retries):
            try:
                await self.rate_limiter.wait_if_needed()

                response = await asyncio.to_thread(
                    text_model.generate_content,
                    prompt
                )

                if response.text:
                    return response.text
                else:
                    logger.warning("Empty response from Gemini")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)

            except Exception as e:
                logger.warning(f"Gemini API error (attempt {attempt + 1}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)

        return ""

    def is_configured(self) -> bool:
        """Check if Gemini API is configured."""
        return bool(settings.GEMINI_API_KEY)


# Global singleton instance
gemini_service = GeminiService()
