from pydantic import BaseModel

from app.types.video import VideoSummary


class DailyUploadCount(BaseModel):
    date: str
    uploads: int


class UploadStats(BaseModel):
    total_files: int
    total_size_bytes: int
    total_size_human: str
    uploads_today: int
    total_downloads: int


class PipelineStats(BaseModel):
    """Dashboard headline metrics for the sports-highlights pipeline."""

    videos_analyzed: int
    highlights_generated: int
    moments_detected: int
    footage_minutes: float
    # Most recent analyses (live status for in-flight jobs).
    recent: list[VideoSummary]
