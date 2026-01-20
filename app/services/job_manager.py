"""
Job manager service for async transcription jobs.
"""
import uuid
from enum import Enum
from typing import Dict, Optional, Any
from datetime import datetime
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class JobStatus(str, Enum):
    """Status of a transcription job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Job:
    """Represents a transcription job."""

    def __init__(self, job_id: str, youtube_url: str, language: Optional[str] = None):
        self.job_id = job_id
        self.youtube_url = youtube_url
        self.language = language
        self.status = JobStatus.PENDING
        self.progress = "Queued"
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.created_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for API response."""
        data = {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": self.progress,
            "created_at": self.created_at.isoformat(),
        }

        if self.status == JobStatus.COMPLETED and self.result:
            data["result"] = self.result
        elif self.status == JobStatus.FAILED and self.error:
            data["error"] = self.error

        if self.completed_at:
            data["completed_at"] = self.completed_at.isoformat()

        return data


class JobManager:
    """Manages transcription jobs."""

    def __init__(self):
        self.jobs: Dict[str, Job] = {}

    def create_job(self, youtube_url: str, language: Optional[str] = None) -> str:
        """Create a new job and return its ID."""
        job_id = str(uuid.uuid4())[:8]
        self.jobs[job_id] = Job(job_id, youtube_url, language)
        logger.info(f"Created job {job_id} for URL: {youtube_url}")
        return job_id

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        return self.jobs.get(job_id)

    def set_processing(self, job_id: str):
        """Mark job as processing."""
        if job := self.jobs.get(job_id):
            job.status = JobStatus.PROCESSING
            logger.info(f"Job {job_id} started processing")

    def update_progress(self, job_id: str, progress: str):
        """Update job progress message."""
        if job := self.jobs.get(job_id):
            job.progress = progress
            logger.debug(f"Job {job_id} progress: {progress}")

    def complete_job(self, job_id: str, result: Dict[str, Any]):
        """Mark job as completed with results."""
        if job := self.jobs.get(job_id):
            job.status = JobStatus.COMPLETED
            job.result = result
            job.progress = "Completed"
            job.completed_at = datetime.utcnow()
            logger.info(f"Job {job_id} completed successfully")

    def fail_job(self, job_id: str, error: str):
        """Mark job as failed with error message."""
        if job := self.jobs.get(job_id):
            job.status = JobStatus.FAILED
            job.error = error
            job.progress = "Failed"
            job.completed_at = datetime.utcnow()
            logger.error(f"Job {job_id} failed: {error}")

    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Remove jobs older than max_age_hours."""
        now = datetime.utcnow()
        to_remove = []
        for job_id, job in self.jobs.items():
            age = (now - job.created_at).total_seconds() / 3600
            if age > max_age_hours:
                to_remove.append(job_id)

        for job_id in to_remove:
            del self.jobs[job_id]
            logger.info(f"Cleaned up old job: {job_id}")


# Global instance
job_manager = JobManager()
