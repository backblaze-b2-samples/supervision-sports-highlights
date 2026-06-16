"""B2 (S3) data access for the sports-highlights pipeline.

All keys live under `settings.video_prefix`. The manifest.json per video is
the single source of truth (status + moment index + search index); there is
no database. boto3 stays confined to this layer.
"""

import logging

from botocore.exceptions import ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client
from app.types import Video, VideoStatus

logger = logging.getLogger(__name__)


# ----- Key builders (scoped to settings.video_prefix) -----


def _base(video_id: str) -> str:
    return f"{settings.video_prefix}videos/{video_id}/"


def source_key(video_id: str, ext: str) -> str:
    ext = ext.lstrip(".") or "mp4"
    return f"{_base(video_id)}source.{ext}"


def manifest_key(video_id: str) -> str:
    return f"{_base(video_id)}manifest.json"


def annotated_key(video_id: str) -> str:
    return f"{_base(video_id)}annotated.mp4"


def clip_key(video_id: str, n: int) -> str:
    return f"{_base(video_id)}clips/moment-{n}.mp4"


def moment_json_key(video_id: str, n: int) -> str:
    return f"{_base(video_id)}moments/moment-{n}.json"


def summary_key(video_id: str, n: int) -> str:
    return f"{_base(video_id)}summaries/moment-{n}.txt"


def thumb_key(video_id: str, n: int) -> str:
    return f"{_base(video_id)}thumbs/moment-{n}.jpg"


# ----- Object IO -----


def put_bytes(key: str, data: bytes, content_type: str) -> None:
    """Upload raw bytes to B2. Raises RuntimeError on failure."""
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=settings.b2_bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 put failed for '{key}': {e}") from e


def put_file(key: str, path: str, content_type: str) -> None:
    """Stream a local file up to B2. Raises RuntimeError on failure."""
    client = get_s3_client()
    try:
        with open(path, "rb") as fh:
            client.put_object(
                Bucket=settings.b2_bucket_name,
                Key=key,
                Body=fh,
                ContentType=content_type,
            )
    except (ClientError, OSError) as e:
        raise RuntimeError(f"B2 put_file failed for '{key}': {e}") from e


def get_bytes(key: str) -> bytes | None:
    """Download an object's bytes. Returns None if it doesn't exist."""
    client = get_s3_client()
    try:
        resp = client.get_object(Bucket=settings.b2_bucket_name, Key=key)
        return resp["Body"].read()
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey"):
            return None
        raise RuntimeError(f"B2 get failed for '{key}': {e}") from e


def download_to(key: str, dest_path: str) -> None:
    """Download an object to a local path. Raises RuntimeError on failure."""
    client = get_s3_client()
    try:
        client.download_file(settings.b2_bucket_name, key, dest_path)
    except ClientError as e:
        raise RuntimeError(f"B2 download failed for '{key}': {e}") from e


def presign_get(key: str, expires_in: int = 3600) -> str:
    """Presigned GET URL for inline streaming (range-friendly, no
    attachment disposition so the browser <video> tag can seek)."""
    client = get_s3_client()
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.b2_bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )
    except ClientError as e:
        raise RuntimeError(f"B2 presign failed for '{key}': {e}") from e


# ----- Manifest (status + moment/search index) -----


def write_manifest(video: Video) -> None:
    put_bytes(
        manifest_key(video.id),
        video.model_dump_json(indent=2).encode("utf-8"),
        "application/json",
    )


def read_manifest(video_id: str) -> Video | None:
    raw = get_bytes(manifest_key(video_id))
    if raw is None:
        return None
    try:
        return Video.model_validate_json(raw)
    except ValueError:
        logger.warning("Corrupt manifest for video %s", video_id)
        return None


# ----- Scoped listing & deletion -----


def list_video_ids() -> list[str]:
    """List every analyzed video id under this app's prefix (one per
    manifest.json), newest objects first by LastModified."""
    client = get_s3_client()
    prefix = f"{settings.video_prefix}videos/"
    found: list[tuple[str, object]] = []
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": prefix, "MaxKeys": 1000}
    try:
        while True:
            resp = client.list_objects_v2(**kwargs)
            for obj in resp.get("Contents", []):
                key = obj["Key"]
                if key.endswith("/manifest.json"):
                    vid = key[len(prefix):].split("/", 1)[0]
                    found.append((vid, obj["LastModified"]))
            if not resp.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = resp["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 list failed: {e}") from e
    found.sort(key=lambda t: t[1], reverse=True)
    return [vid for vid, _ in found]


def delete_video_prefix(video_id: str) -> int:
    """Delete a single video and every derived asset under its prefix ONLY.

    Scoped to `…/videos/{video_id}/` — never touches other videos or other
    apps' prefixes. Returns the number of objects deleted.
    """
    client = get_s3_client()
    prefix = _base(video_id)
    deleted = 0
    kwargs: dict = {"Bucket": settings.b2_bucket_name, "Prefix": prefix, "MaxKeys": 1000}
    try:
        while True:
            resp = client.list_objects_v2(**kwargs)
            objects = [{"Key": o["Key"]} for o in resp.get("Contents", [])]
            if objects:
                client.delete_objects(
                    Bucket=settings.b2_bucket_name,
                    Delete={"Objects": objects},
                )
                deleted += len(objects)
            if not resp.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = resp["NextContinuationToken"]
    except ClientError as e:
        raise RuntimeError(f"B2 scoped delete failed for '{prefix}': {e}") from e
    return deleted


__all__ = [
    "VideoStatus",
    "annotated_key",
    "clip_key",
    "delete_video_prefix",
    "download_to",
    "get_bytes",
    "list_video_ids",
    "manifest_key",
    "moment_json_key",
    "presign_get",
    "put_bytes",
    "put_file",
    "read_manifest",
    "source_key",
    "summary_key",
    "thumb_key",
    "write_manifest",
]
