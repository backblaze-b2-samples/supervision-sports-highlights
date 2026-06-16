"""ffmpeg / ffprobe subprocess wrappers.

These shell out to the system `ffmpeg` and `ffprobe` binaries (documented
install in the README — they are NOT pip packages). Kept in the repo layer
because they are an external dependency the service layer must not call
directly.
"""

import json
import logging
import subprocess

logger = logging.getLogger(__name__)


class MediaError(RuntimeError):
    """Raised when ffmpeg/ffprobe fails."""


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            cmd, capture_output=True, check=True, text=True
        )
    except FileNotFoundError as e:
        raise MediaError(
            f"'{cmd[0]}' not found on PATH — install ffmpeg (see README)."
        ) from e
    except subprocess.CalledProcessError as e:
        tail = (e.stderr or "")[-500:]
        raise MediaError(f"{cmd[0]} failed: {tail}") from e


def probe(path: str) -> dict:
    """Return {duration_seconds, fps, width, height, codec, bitrate} for a
    local video file using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries",
        "stream=width,height,avg_frame_rate,codec_name:format=duration,bit_rate",
        "-of", "json", path,
    ]
    out = _run(cmd).stdout
    data = json.loads(out)
    stream = (data.get("streams") or [{}])[0]
    fmt = data.get("format") or {}

    fps = None
    rate = stream.get("avg_frame_rate")
    if rate and "/" in rate:
        num, den = rate.split("/")
        if float(den) != 0:
            fps = round(float(num) / float(den), 3)

    duration = float(fmt["duration"]) if fmt.get("duration") else None
    bitrate = int(fmt["bit_rate"]) if fmt.get("bit_rate") else None

    return {
        "duration_seconds": duration,
        "fps": fps,
        "width": int(stream["width"]) if stream.get("width") else None,
        "height": int(stream["height"]) if stream.get("height") else None,
        "codec": stream.get("codec_name"),
        "bitrate": bitrate,
    }


def cut_clip(src_path: str, dest_path: str, start_s: float, end_s: float) -> None:
    """Cut a highlight clip with stream copy (fast, no re-encode)."""
    duration = max(0.1, end_s - start_s)
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start_s:.3f}",
        "-i", src_path,
        "-t", f"{duration:.3f}",
        "-c", "copy",
        "-avoid_negative_ts", "make_zero",
        dest_path,
    ]
    _run(cmd)


def extract_frame(src_path: str, dest_path: str, at_s: float) -> None:
    """Extract a single JPEG keyframe at a timestamp (for thumbnails)."""
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{at_s:.3f}",
        "-i", src_path,
        "-frames:v", "1",
        "-q:v", "3",
        dest_path,
    ]
    _run(cmd)


def encode_from_frames(
    frames_dir: str, pattern: str, fps: float, dest_path: str
) -> None:
    """Encode an annotated mp4 from a directory of numbered JPEG frames."""
    cmd = [
        "ffmpeg", "-y",
        "-framerate", f"{fps:.3f}",
        "-i", f"{frames_dir}/{pattern}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        dest_path,
    ]
    _run(cmd)
