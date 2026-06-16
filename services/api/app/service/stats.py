"""Dashboard aggregation for the sports-highlights pipeline.

Scans this app's manifests and rolls them up into headline metrics +
a recent-analyses list (with live status for in-flight jobs).
"""

from app.repo import video_store as store
from app.types import PipelineStats, VideoStatus, VideoSummary

RECENT_LIMIT = 8


def get_pipeline_stats() -> PipelineStats:
    videos_analyzed = 0
    highlights_generated = 0
    moments_detected = 0
    footage_seconds = 0.0
    recent: list[VideoSummary] = []

    for vid in store.list_video_ids():
        video = store.read_manifest(vid)
        if video is None:
            continue
        videos_analyzed += 1
        moments_detected += video.moment_count
        # A "highlight" is a moment that produced a playable clip.
        highlights_generated += sum(
            1 for m in video.moments if m.clip_key is not None
        )
        if video.status == VideoStatus.READY and video.duration_seconds:
            footage_seconds += video.duration_seconds

        if len(recent) < RECENT_LIMIT:
            thumb_url = None
            if video.moments and video.moments[0].thumb_key:
                thumb_url = store.presign_get(video.moments[0].thumb_key)
            recent.append(
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

    return PipelineStats(
        videos_analyzed=videos_analyzed,
        highlights_generated=highlights_generated,
        moments_detected=moments_detected,
        footage_minutes=round(footage_seconds / 60.0, 1),
        recent=recent,
    )
