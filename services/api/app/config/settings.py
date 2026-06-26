import re
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings

B2_REGION_RE = re.compile(r"^[a-z]+(?:-[a-z]+)*-\d{3}$")


def _normalize_b2_region(value: str) -> str:
    region = value.strip()
    if not region:
        return ""
    if not B2_REGION_RE.fullmatch(region):
        raise ValueError(
            "B2_REGION must be a Backblaze region slug like 'us-west-004'"
        )
    return region


class Settings(BaseSettings):
    # --- Backblaze B2 (S3-compatible) ---
    b2_application_key_id: str = ""
    b2_application_key: str = ""
    b2_bucket_name: str = ""
    b2_region: str = ""
    b2_public_url_base: str = ""

    api_port: int = 8000
    # Explicit allowlist by default — covers Next on :3000 and the
    # fallback :3001 it picks if 3000 is busy. Production deploys should
    # override with the exact frontend origin.
    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    # Optional dev-only escape hatch: a regex that matches additional
    # allowed origins. Empty by default — set this to e.g.
    # `^http://localhost:\d+$` to accept any localhost port without
    # listing each one. NEVER ship this to production.
    api_cors_origin_regex: str = ""

    # Upload limits. Sports clips are large; allow up to 500MB by default.
    max_file_size: int = 500 * 1024 * 1024  # 500MB

    # Small durable counter for the /files browser's download stats. Point at
    # a persistent volume in production if you care about surviving restarts.
    download_count_file: str = "data/download_count.json"

    # --- AI moment summaries (Anthropic Claude) ---
    # Optional: if absent, the pipeline still detects, clips, and annotates;
    # moments fall back to a templated description. See README.
    anthropic_api_key: str = ""
    summary_model: str = "claude-haiku-4-5"

    # --- Computer-vision pipeline (Roboflow Inference + Supervision) ---
    # Pre-trained COCO model id, runs locally with NO key. A smaller/faster
    # id is fine on CPU. ROBOFLOW_API_KEY (optional) unlocks Universe
    # sport-specific models + hosted serverless inference.
    detection_model: str = "rfdetr-base"
    roboflow_api_key: str = ""
    # Class-name → semantic-role mapping for the highlight heuristic. The
    # keyless COCO default (`rfdetr-base`) emits "person"/"sports ball", so the
    # defaults below reproduce the original behavior exactly. Roboflow Universe
    # sport-specific models emit custom labels (e.g. "player", "basketball"),
    # so override these (comma-separated, case-insensitive) to keep the
    # person/ball heuristic working — otherwise it collapses to motion-only.
    detection_person_classes: str = "person"
    detection_ball_classes: str = "sports ball"
    # Analyze every Nth frame to keep CPU runtime tractable. ByteTrack
    # carries IDs between analyzed frames; the annotated render carries
    # forward the latest detections so output looks full-FPS.
    analyze_stride: int = 3
    # Cap the highlight timeline to the top-N moments by intensity.
    max_moments: int = 8

    # --- B2 prefix scoping ---
    # Every artifact this app writes lives under this prefix. The /highlights
    # library lists only this prefix; /files browses the full bucket.
    video_prefix: str = "supervision-sports-highlights/"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @field_validator("b2_region")
    @classmethod
    def validate_b2_region(cls, value: str) -> str:
        return _normalize_b2_region(value)

    @property
    def normalized_b2_region(self) -> str:
        return _normalize_b2_region(self.b2_region)

    @property
    def b2_s3_endpoint_url(self) -> str:
        return f"https://s3.{self.normalized_b2_region}.backblazeb2.com"

    @property
    def normalized_b2_public_url_base(self) -> str:
        return self.b2_public_url_base.strip().rstrip("/")

    @property
    def has_https_b2_public_url_base(self) -> bool:
        public_url = self.normalized_b2_public_url_base
        if not public_url:
            return True
        parsed = urlparse(public_url)
        return parsed.scheme == "https" and bool(parsed.netloc)

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",")]

    @staticmethod
    def _normalize_classes(raw: str) -> set[str]:
        """Comma-separated class names → a lower-cased, trimmed, non-empty set."""
        return {c.strip().lower() for c in raw.split(",") if c.strip()}

    @property
    def person_class_set(self) -> set[str]:
        return self._normalize_classes(self.detection_person_classes)

    @property
    def ball_class_set(self) -> set[str]:
        return self._normalize_classes(self.detection_ball_classes)


settings = Settings()
