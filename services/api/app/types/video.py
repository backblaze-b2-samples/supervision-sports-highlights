from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel

from app.types.moment import Moment


class VideoStatus(StrEnum):
    """Lifecycle of an analysis job, persisted in the video's manifest.json.

    The frontend polls while any video is in a non-terminal state and stops
    once every job reaches `ready` or `failed`.
    """

    UPLOADED = "uploaded"
    PROBING = "probing"
    DETECTING = "detecting"
    CLIPPING = "clipping"
    ANNOTATING = "annotating"
    SUMMARIZING = "summarizing"
    READY = "ready"
    FAILED = "failed"


# States from which the pipeline is still working — the UI polls in these.
ACTIVE_STATUSES = {
    VideoStatus.UPLOADED,
    VideoStatus.PROBING,
    VideoStatus.DETECTING,
    VideoStatus.CLIPPING,
    VideoStatus.ANNOTATING,
    VideoStatus.SUMMARIZING,
}


class Video(BaseModel):
    """A registered sports video and the state of its analysis pipeline.

    Serialized to `…/videos/{id}/manifest.json` on B2 — the manifest is the
    single source of truth (also the search index). There is no database.
    """

    id: str
    filename: str
    status: VideoStatus = VideoStatus.UPLOADED
    source_key: str
    annotated_key: str | None = None
    error: str | None = None
    # ffprobe-derived
    duration_seconds: float | None = None
    fps: float | None = None
    width: int | None = None
    height: int | None = None
    # Pipeline outputs
    moments: list[Moment] = []
    moment_count: int = 0
    # Whether AI summaries were generated (false ⇒ templated fallback used).
    ai_summaries: bool = False
    created_at: datetime
    updated_at: datetime


class VideoSummary(BaseModel):
    """Lightweight projection for the Highlights Library list view."""

    id: str
    filename: str
    status: VideoStatus
    moment_count: int
    duration_seconds: float | None = None
    thumb_url: str | None = None
    created_at: datetime
    updated_at: datetime
