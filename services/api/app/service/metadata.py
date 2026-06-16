import hashlib
import logging
from datetime import UTC, datetime

from app.types import FileMetadataDetail
from app.types.formatting import humanize_bytes

logger = logging.getLogger(__name__)


def extract_metadata(
    file_data: bytes,
    filename: str,
    content_type: str,
) -> FileMetadataDetail:
    """Compute basic file metadata: size, type, extension, checksums.

    This app stores sports videos, so it does not parse image EXIF or PDF
    structure (the starter kit's Pillow/PyPDF2 extraction was trimmed). Rich
    video analysis happens in the CV pipeline (see service/analyze.py), not
    here at upload time.
    """
    md5 = hashlib.md5(file_data, usedforsecurity=False).hexdigest()
    sha256 = hashlib.sha256(file_data).hexdigest()
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    return FileMetadataDetail(
        filename=filename,
        size_bytes=len(file_data),
        size_human=humanize_bytes(len(file_data)),
        mime_type=content_type,
        extension=extension,
        md5=md5,
        sha256=sha256,
        uploaded_at=datetime.now(UTC),
    )
