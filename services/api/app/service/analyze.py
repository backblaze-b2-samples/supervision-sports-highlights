"""Pipeline orchestrator: probe → detect+track → moments → clips → annotate
→ summarize → manifest.

Runs in a FastAPI BackgroundTask. Status is persisted to the video's
manifest.json on B2 at each stage so the frontend can poll live progress.
Degrades gracefully when ANTHROPIC_API_KEY is absent (templated descriptions).
The orchestrator owns no CV types — it delegates to repo adapters and reasons
over plain FrameStat objects.
"""

import logging
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from app.config import settings
from app.repo import llm, media, video_pipeline
from app.repo import video_store as store
from app.service.moments import FrameStat, detect_moments
from app.service.summarize import build_prompt, fallback
from app.types import Moment, Video, VideoStatus

logger = logging.getLogger(__name__)


def _touch(video: Video, status: VideoStatus) -> None:
    video.status = status
    video.updated_at = datetime.now(UTC)
    store.write_manifest(video)
    logger.info("video=%s status=%s", video.id, status.value)


def run_pipeline(video_id: str) -> None:
    """Entry point for the BackgroundTask. Never raises — failures are
    recorded on the manifest as status=failed."""
    video = store.read_manifest(video_id)
    if video is None:
        logger.error("run_pipeline: no manifest for %s", video_id)
        return
    try:
        with tempfile.TemporaryDirectory(prefix=f"ssh-{video_id}-") as tmp:
            _run(video, Path(tmp))
    except Exception as e:
        logger.exception("Pipeline failed for %s", video_id)
        video.error = str(e)[:500]
        _touch(video, VideoStatus.FAILED)


def _run(video: Video, tmp: Path) -> None:
    ext = video.source_key.rsplit(".", 1)[-1]
    src = tmp / f"source.{ext}"

    _touch(video, VideoStatus.PROBING)
    store.download_to(video.source_key, str(src))
    info = media.probe(str(src))
    video.duration_seconds = info["duration_seconds"]
    video.fps = info["fps"]
    video.width = info["width"]
    video.height = info["height"]
    store.write_manifest(video)

    # --- Detect + track every Nth frame; render annotated video ---
    _touch(video, VideoStatus.DETECTING)
    stats: list[FrameStat] = []

    def on_stat(t: float, s: dict) -> None:
        stats.append(
            FrameStat(
                t=t,
                person_count=s["person_count"],
                ball_present=s["ball_present"],
                motion=s["motion"],
                track_ids=set(s["track_ids"]),
                detection_count=s["detection_count"],
            )
        )

    frames_dir = tmp / "frames"
    annotated = tmp / "annotated.mp4"
    fps = video_pipeline.analyze_and_annotate(
        str(src), str(frames_dir), str(annotated),
        stride=settings.analyze_stride, on_stat=on_stat,
    )
    video.fps = video.fps or fps

    _touch(video, VideoStatus.ANNOTATING)
    if annotated.exists():
        akey = store.annotated_key(video.id)
        store.put_file(akey, str(annotated), "video/mp4")
        video.annotated_key = akey
        store.write_manifest(video)

    # --- Moment detection + clips + thumbs ---
    _touch(video, VideoStatus.CLIPPING)
    detected = detect_moments(stats, max_moments=settings.max_moments)
    moments: list[Moment] = []
    for i, dm in enumerate(detected):
        clip = tmp / f"clip-{i}.mp4"
        thumb = tmp / f"thumb-{i}.jpg"
        clip_key = thumb_key = None
        try:
            media.cut_clip(str(src), str(clip), dm.start_s, dm.end_s)
            clip_key = store.clip_key(video.id, i)
            store.put_file(clip_key, str(clip), "video/mp4")
        except media.MediaError as e:
            logger.warning("Clip %d failed for %s: %s", i, video.id, e)
        try:
            media.extract_frame(str(src), str(thumb), dm.peak_t)
            thumb_key = store.thumb_key(video.id, i)
            store.put_file(thumb_key, str(thumb), "image/jpeg")
        except media.MediaError as e:
            logger.warning("Thumb %d failed for %s: %s", i, video.id, e)

        moments.append(
            Moment(
                id=i, start_s=round(dm.start_s, 2), end_s=round(dm.end_s, 2),
                score=dm.score, peak_person_count=dm.peak_person_count,
                unique_track_ids=dm.unique_track_ids, ball_present=dm.ball_present,
                detection_count=dm.detection_count,
                clip_key=clip_key, thumb_key=thumb_key,
            )
        )
    video.moments = moments
    video.moment_count = len(moments)
    store.write_manifest(video)

    # --- AI summaries (graceful fallback) ---
    _touch(video, VideoStatus.SUMMARIZING)
    video.ai_summaries = llm.is_available()
    for m in moments:
        text = _summarize(m, video)
        m.summary = text["summary"]
        m.description = text["description"]
        m.tags = text["tags"]
        store.put_bytes(
            store.summary_key(video.id, m.id),
            m.description.encode("utf-8"), "text/plain",
        )
        store.put_bytes(
            store.moment_json_key(video.id, m.id),
            m.model_dump_json(indent=2).encode("utf-8"), "application/json",
        )

    _touch(video, VideoStatus.READY)


def _summarize(moment: Moment, video: Video) -> dict:
    if not llm.is_available():
        return fallback(moment)
    try:
        return llm.summarize_moment(build_prompt(moment, video))
    except Exception as e:
        logger.warning("LLM summary failed for moment %d: %s", moment.id, e)
        return fallback(moment)
