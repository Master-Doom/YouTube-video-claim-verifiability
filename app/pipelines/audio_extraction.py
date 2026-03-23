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

        Tries two strategies in order:
        1. tv_embedded client without cookies (reliable from data center IPs)
        2. web client with cookies (fallback, only if cookies are configured)

        Args:
            youtube_url: YouTube video URL

        Returns:
            Tuple of (audio_file_path, metadata_dict)

        Raises:
            Exception: If all download attempts fail
        """
        try:
            logger.info(f"Starting download from: {youtube_url}")

            output_path = get_unique_filename(settings.TEMP_DIR, "yt_audio_", "wav")

            base_opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'wav'}],
                'outtmpl': output_path.replace('.wav', ''),
                'quiet': False,
                'no_warnings': False,
                'extract_flat': False,
                'postprocessor_args': ['-ar', '16000', '-ac', '1'],
            }

            # Attempt 1: web client with cookies — Deno (installed in Docker) solves the n-challenge
            # Cookies are required from data center IPs to bypass YouTube's bot detection
            attempts = []
            if self._cookies_path:
                attempts.append(('web (with cookies)', {
                    **base_opts,
                    'extractor_args': {'youtube': {'player_client': ['web']}},
                    'cookiefile': self._cookies_path,
                }))

            # Attempt 2: web client without cookies — fallback for public videos
            attempts.append(('web (no cookies)', {
                **base_opts,
                'extractor_args': {'youtube': {'player_client': ['web']}},
            }))

            info = None
            last_error = None

            for label, opts in attempts:
                try:
                    logger.info(f"Download attempt: {label}")
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(youtube_url, download=False)

                        duration = info.get('duration', 0)
                        if duration > settings.max_video_length_seconds:
                            raise ValueError(
                                f"{ERROR_VIDEO_TOO_LONG}: {duration/60:.1f} minutes "
                                f"(max: {settings.MAX_VIDEO_LENGTH_MINUTES} minutes)"
                            )

                        logger.info(f"Video title: {info.get('title', 'Unknown')}")
                        logger.info(f"Duration: {duration/60:.1f} minutes")
                        logger.info("Downloading audio...")
                        ydl.download([youtube_url])
                    break  # success — stop trying
                except ValueError:
                    raise
                except Exception as e:
                    logger.warning(f"Attempt '{label}' failed: {e}")
                    last_error = e
                    info = None

            if info is None:
                raise last_error or Exception("All download attempts failed")

            metadata = {
                'title': info.get('title', 'Unknown'),
                'duration': info.get('duration', 0),
                'uploader': info.get('uploader', 'Unknown'),
                'upload_date': info.get('upload_date', 'Unknown'),
                'view_count': info.get('view_count', 0),
                'description': info.get('description', '')[:500],
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
