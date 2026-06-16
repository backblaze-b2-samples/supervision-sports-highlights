"""Video registration, listing, retrieval, playback URLs, and scoped delete.

The CV pipeline itself lives in analyze.py; this module is the read/write
surface the runtime layer talks to. All deletes are scoped to a single
video's prefix — they never touch other videos or other apps' data.
"""

import logging
import re
import uuid
from datetime import UTC, datetime

from app.repo import video_store as store
from app.types import (
    MomentPlayback,
    Video,
    VideoStatus,
    VideoSummary,
)

logger = logging.getLogger(__name__)

ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime", "video/webm"}
_TYPE_EXT = {"video/mp4": "mp4", "video/quicktime": "mov", "video/webm": "webm"}
_ID_RE = re.compile(r"^[a-f0-9]{32}$")


class VideoError(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class VideoNotFound(Exception):
    def __init__(self, detail: str = "Video not found"):
        self.detail = detail
        super().__init__(detail)


def _validate_id(video_id: str) -> None:
    if not _ID_RE.match(video_id):
        raise VideoError("Invalid video id")


def register_upload(
    data: bytes, filename: str, content_type: str
) -> Video:
    """Store the source video on B2 and write the initial manifest. Returns
    the registered Video (status=uploaded). The caller kicks off the pipeline."""
    if content_type not in ALLOWED_VIDEO_TYPES:
        raise VideoError(
            f"Unsupported video type '{content_type}'. Use mp4, mov, or webm.",
            status_code=415,
        )
    if not data:
        raise VideoError("Empty file")

    video_id = uuid.uuid4().hex
    ext = _TYPE_EXT.get(content_type, "mp4")
    src_key = store.source_key(video_id, ext)
    store.put_bytes(src_key, data, content_type)

    now = datetime.now(UTC)
    video = Video(
        id=video_id,
        filename=filename or f"clip.{ext}",
        status=VideoStatus.UPLOADED,
        source_key=src_key,
        created_at=now,
        updated_at=now,
    )
    store.write_manifest(video)
    logger.info("Registered video %s (%s)", video_id, video.filename)
    return video


def get_video(video_id: str) -> Video:
    _validate_id(video_id)
    video = store.read_manifest(video_id)
    if video is None:
        raise VideoNotFound()
    return video


def list_videos() -> list[VideoSummary]:
    summaries: list[VideoSummary] = []
    for vid in store.list_video_ids():
        video = store.read_manifest(vid)
        if video is None:
            continue
        thumb_url = None
        if video.moments and video.moments[0].thumb_key:
            thumb_url = store.presign_get(video.moments[0].thumb_key)
        summaries.append(
            VideoSummary(
                id=video.id,
                filename=video.filename,
                status=video.status,
                moment_count=video.moment_count,
                duration_seconds=video.duration_seconds,
                thumb_url=thumb_url,
                created_at=video.created_at,
                updated_at=video.updated_at,
            )
        )
    return summaries


def annotated_playback_url(video_id: str) -> str | None:
    video = get_video(video_id)
    if not video.annotated_key:
        return None
    return store.presign_get(video.annotated_key)


def moments_with_media(video_id: str) -> list[MomentPlayback]:
    """Return each moment enriched with presigned, range-friendly B2 URLs for
    its clip and thumbnail (streamed straight from B2 by the browser)."""
    video = get_video(video_id)
    out: list[MomentPlayback] = []
    for m in video.moments:
        out.append(
            MomentPlayback(
                moment=m,
                clip_url=store.presign_get(m.clip_key) if m.clip_key else None,
                thumb_url=store.presign_get(m.thumb_key) if m.thumb_key else None,
            )
        )
    return out


def delete_video(video_id: str) -> int:
    """Delete a video and ALL its derived assets — scoped to that video's
    prefix only. Returns the number of B2 objects removed."""
    _validate_id(video_id)
    if store.read_manifest(video_id) is None:
        raise VideoNotFound()
    count = store.delete_video_prefix(video_id)
    logger.info("Deleted video %s (%d objects)", video_id, count)
    return count


def mark_reanalyzing(video_id: str) -> Video:
    """Reset a video to `uploaded` so the pipeline can re-run on it."""
    video = get_video(video_id)
    video.status = VideoStatus.UPLOADED
    video.error = None
    video.moments = []
    video.moment_count = 0
    video.updated_at = datetime.now(UTC)
    store.write_manifest(video)
    return video
