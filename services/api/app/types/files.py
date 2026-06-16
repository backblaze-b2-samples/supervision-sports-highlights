from datetime import datetime

from pydantic import BaseModel


class FileMetadata(BaseModel):
    key: str
    filename: str
    folder: str
    size_bytes: int
    size_human: str
    content_type: str
    uploaded_at: datetime
    url: str | None = None


class FileMetadataDetail(BaseModel):
    filename: str
    size_bytes: int
    size_human: str
    mime_type: str
    extension: str
    md5: str
    sha256: str
    uploaded_at: datetime
    # Video-specific (populated by the CV pipeline's ffprobe step, not at
    # upload time). Image EXIF / PDF parsing was trimmed — this app handles
    # sports video only.
    duration_seconds: float | None = None
    codec: str | None = None
    bitrate: int | None = None
