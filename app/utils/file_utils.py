"""
File utility functions.
"""
import os
import shutil
from pathlib import Path
from typing import Optional
from app.utils.logger import setup_logger
from app.core.config import settings

logger = setup_logger(__name__)


def ensure_dir(directory: str) -> Path:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        directory: Directory path

    Returns:
        Path object for the directory
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def cleanup_temp_file(file_path: Optional[str]) -> None:
    """
    Safely delete a temporary file.

    Args:
        file_path: Path to the file to delete
    """
    if not file_path:
        return

    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up temporary file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup file {file_path}: {e}")


def cleanup_temp_directory(directory: Optional[str] = None) -> None:
    """
    Clean up all files in the temporary directory.

    Args:
        directory: Directory to clean (defaults to TEMP_DIR from settings)
    """
    target_dir = directory or settings.TEMP_DIR

    try:
        if os.path.exists(target_dir):
            for filename in os.listdir(target_dir):
                file_path = os.path.join(target_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            logger.info(f"Cleaned up temporary directory: {target_dir}")
    except Exception as e:
        logger.warning(f"Failed to cleanup directory {target_dir}: {e}")


def get_file_size_mb(file_path: str) -> float:
    """
    Get file size in megabytes.

    Args:
        file_path: Path to the file

    Returns:
        File size in MB
    """
    if not os.path.exists(file_path):
        return 0.0
    return os.path.getsize(file_path) / (1024 * 1024)


def validate_file_path(file_path: str, must_exist: bool = True) -> bool:
    """
    Validate a file path for security and existence.

    Args:
        file_path: Path to validate
        must_exist: Whether the file must exist

    Returns:
        True if valid, False otherwise
    """
    try:
        path = Path(file_path).resolve()

        # Check if path is within allowed directories
        temp_dir = Path(settings.TEMP_DIR).resolve()
        models_dir = Path(settings.MODELS_DIR).resolve()

        is_in_temp = temp_dir in path.parents or path == temp_dir
        is_in_models = models_dir in path.parents or path == models_dir

        if not (is_in_temp or is_in_models):
            logger.warning(f"File path outside allowed directories: {file_path}")
            return False

        if must_exist and not path.exists():
            logger.warning(f"File does not exist: {file_path}")
            return False

        return True
    except Exception as e:
        logger.error(f"Error validating file path {file_path}: {e}")
        return False


def get_unique_filename(directory: str, prefix: str, extension: str) -> str:
    """
    Generate a unique filename in the specified directory.

    Args:
        directory: Target directory
        prefix: Filename prefix
        extension: File extension (with or without dot)

    Returns:
        Full path to the unique filename
    """
    import uuid

    if not extension.startswith("."):
        extension = f".{extension}"

    unique_id = str(uuid.uuid4())[:8]
    filename = f"{prefix}{unique_id}{extension}"
    return os.path.join(directory, filename)
