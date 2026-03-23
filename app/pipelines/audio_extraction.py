"""
YouTube audio extraction pipeline.
"""
import base64
import os
import yt_dlp
from typing import Tuple, Dict
from app.utils.logger import setup_logger
from app.utils.file_utils import get_unique_filename, ensure_dir
from app.core.config import settings
from app.core.constants import ERROR_DOWNLOAD_FAILED, ERROR_VIDEO_TOO_LONG

logger = setup_logger(__name__)


class AudioExtractor:
    """Handles YouTube video download and audio extraction."""

    def __init__(self):
        """Initialize the audio extractor."""
        ensure_dir(settings.TEMP_DIR)
        self._cookies_path = self._resolve_cookies_path()

    def _resolve_cookies_path(self) -> str:
        """Resolve cookies file path, decoding base64 secret if provided."""
        # Priority 1: base64-encoded secret (for HF Spaces)
        if settings.YOUTUBE_COOKIES_BASE64:
            cookies_path = os.path.join(settings.TEMP_DIR, "yt_cookies.txt")
            try:
                decoded = base64.b64decode(settings.YOUTUBE_COOKIES_BASE64)
                with open(cookies_path, "wb") as f:
                    f.write(decoded)
                logger.info("YouTube cookies decoded from YOUTUBE_COOKIES_BASE64")
                return cookies_path
            except Exception as e:
                logger.warning(f"Failed to decode YOUTUBE_COOKIES_BASE64: {e}")
        # Priority 2: explicit file path
        if settings.YOUTUBE_COOKIES_PATH and os.path.exists(settings.YOUTUBE_COOKIES_PATH):
            return settings.YOUTUBE_COOKIES_PATH
        return ""

    def download_and_extract(self, youtube_url: str) -> Tuple[str, Dict]:
        """
        Download YouTube video and extract audio.

        Args:
            youtube_url: YouTube video URL

        Returns:
            Tuple of (audio_file_path, metadata_dict)

        Raises:
            Exception: If download or extraction fails
        """
        try:
            logger.info(f"Starting download from: {youtube_url}")

            # Generate unique output filename
            output_path = get_unique_filename(
                settings.TEMP_DIR,
                "yt_audio_",
                "wav"
            )

            # Configure yt-dlp options with enhanced YouTube compatibility
            ydl_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio/best',  # Prefer m4a, fallback to any audio or combined
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                }],
                'outtmpl': output_path.replace('.wav', ''),
                'quiet': False,
                'no_warnings': False,
                'extract_flat': False,
                'postprocessor_args': [
                    '-ar', str(16000),  # Sample rate
                    '-ac', '1',  # Mono
                ],
                # Enhanced options for YouTube compatibility
                # tv_embedded is designed for server/embedded use and bypasses bot detection on data center IPs
                'extractor_args': {
                    'youtube': {
                        'player_client': ['tv_embedded', 'ios'],
                    }
                },
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'http_headers': {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-us,en;q=0.5',
                    'Sec-Fetch-Mode': 'navigate',
                },
            }

            # Add cookies file if configured (for bypassing bot detection)
            if self._cookies_path:
                ydl_opts['cookiefile'] = self._cookies_path
                logger.info(f"Using YouTube cookies from: {self._cookies_path}")

            # Download and extract metadata
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info("Extracting video information...")
                info = ydl.extract_info(youtube_url, download=False)

                # Check video duration
                duration = info.get('duration', 0)
                if duration > settings.max_video_length_seconds:
                    raise ValueError(
                        f"{ERROR_VIDEO_TOO_LONG}: {duration/60:.1f} minutes "
                        f"(max: {settings.MAX_VIDEO_LENGTH_MINUTES} minutes)"
                    )

                logger.info(f"Video title: {info.get('title', 'Unknown')}")
                logger.info(f"Duration: {duration/60:.1f} minutes")

                # Download audio
                logger.info("Downloading audio...")
                ydl.download([youtube_url])

            # Prepare metadata
            metadata = {
                'title': info.get('title', 'Unknown'),
                'duration': duration,
                'uploader': info.get('uploader', 'Unknown'),
                'upload_date': info.get('upload_date', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'description': info.get('description', '')[:500],  # Limit description length
            }

            logger.info(f"Successfully extracted audio to: {output_path}")
            return output_path, metadata

        except yt_dlp.utils.DownloadError as e:
            logger.error(f"Download failed: {e}")
            raise Exception(f"{ERROR_DOWNLOAD_FAILED}: {str(e)}")
        except ValueError as e:
            logger.error(f"Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during extraction: {e}")
            raise Exception(f"{ERROR_DOWNLOAD_FAILED}: {str(e)}")


# Singleton instance
audio_extractor = AudioExtractor()
