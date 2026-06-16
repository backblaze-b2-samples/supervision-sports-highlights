import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, UploadFile

from app.config import settings
from app.service import stats as stats_service
from app.service import videos as videos_service
from app.service.analyze import run_pipeline
from app.service.videos import VideoError, VideoNotFound
from app.types import (
    MomentPlayback,
    PipelineStats,
    Video,
    VideoSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/videos/stats", response_model=PipelineStats)
async def pipeline_stats_endpoint():
    return stats_service.get_pipeline_stats()


@router.post("/videos", response_model=Video, status_code=201)
async def register_video_endpoint(
    request: Request, file: UploadFile, background: BackgroundTasks
):
    content_type = file.content_type or "application/octet-stream"

    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        total += len(chunk)
        if total > settings.max_file_size:
            raise HTTPException(status_code=413, detail="Video too large")
        chunks.append(chunk)
    data = b"".join(chunks)

    try:
        video = videos_service.register_upload(
            data, file.filename or "", content_type
        )
    except VideoError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None

    # Kick off the CV pipeline asynchronously; status is polled via GET.
    background.add_task(run_pipeline, video.id)
    return video


@router.get("/videos", response_model=list[VideoSummary])
async def list_videos_endpoint():
    return videos_service.list_videos()


@router.get("/videos/{video_id}", response_model=Video)
async def get_video_endpoint(video_id: str):
    try:
        return videos_service.get_video(video_id)
    except VideoError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    except VideoNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.get("/videos/{video_id}/playback")
async def playback_endpoint(video_id: str):
    try:
        url = videos_service.annotated_playback_url(video_id)
    except VideoNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    if url is None:
        raise HTTPException(status_code=404, detail="Annotated video not ready")
    return {"url": url}


@router.get("/videos/{video_id}/moments", response_model=list[MomentPlayback])
async def moments_endpoint(video_id: str):
    try:
        return videos_service.moments_with_media(video_id)
    except VideoNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None


@router.post("/videos/{video_id}/reanalyze", response_model=Video)
async def reanalyze_endpoint(video_id: str, background: BackgroundTasks):
    try:
        video = videos_service.mark_reanalyzing(video_id)
    except VideoNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    background.add_task(run_pipeline, video.id)
    return video


@router.delete("/videos/{video_id}")
async def delete_video_endpoint(video_id: str):
    try:
        count = videos_service.delete_video(video_id)
    except VideoError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from None
    except VideoNotFound as e:
        raise HTTPException(status_code=404, detail=e.detail) from None
    return {"deleted": True, "id": video_id, "objects_removed": count}
