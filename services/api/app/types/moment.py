from pydantic import BaseModel


class Moment(BaseModel):
    """A single detected highlight within a video.

    Stored inside the video manifest and (in full detail) as
    `…/moments/moment-{n}.json`. The summary/description/tags feed the
    Highlights detail view and the `/search` index.
    """

    id: int
    start_s: float
    end_s: float
    # Peak intensity score (0..1-ish, heuristic) that triggered the moment.
    score: float
    # Tracking / detection stats from Supervision ByteTrack.
    peak_person_count: int = 0
    unique_track_ids: int = 0
    ball_present: bool = False
    detection_count: int = 0
    # B2 keys for derived assets (None until that stage completes).
    thumb_key: str | None = None
    clip_key: str | None = None
    # AI (or templated fallback) outputs.
    summary: str = ""
    description: str = ""
    tags: list[str] = []

    @property
    def duration_s(self) -> float:
        return round(self.end_s - self.start_s, 2)


class MomentPlayback(BaseModel):
    """A moment enriched with presigned, range-friendly B2 media URLs for the
    detail view. Returned by the videos runtime, never persisted."""

    moment: Moment
    clip_url: str | None = None
    thumb_url: str | None = None


class SearchHit(BaseModel):
    """A moment matched by the /search endpoint, with its parent video."""

    video_id: str
    video_filename: str
    moment: Moment
