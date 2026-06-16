"""Tests for prompt building and the templated graceful-degradation fallback."""

from app.service.summarize import build_prompt, fallback
from app.types import Moment, Video, VideoStatus


def _moment(**kw) -> Moment:
    base = dict(id=0, start_s=10.0, end_s=14.0, score=0.8)
    base.update(kw)
    return Moment(**base)


def _video() -> Video:
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    return Video(
        id="a" * 32,
        filename="match.mp4",
        status=VideoStatus.SUMMARIZING,
        source_key="p/source.mp4",
        created_at=now,
        updated_at=now,
    )


def test_prompt_includes_track_and_ball_stats():
    prompt = build_prompt(
        _moment(peak_person_count=6, unique_track_ids=4, ball_present=True),
        _video(),
    )
    assert "match.mp4" in prompt
    assert "6" in prompt  # people
    assert "ByteTrack" in prompt
    assert "yes" in prompt  # ball present


def test_fallback_is_self_describing_and_tagged():
    out = fallback(_moment(ball_present=True, peak_person_count=5, score=0.9))
    assert "ANTHROPIC_API_KEY" in out["description"]
    assert "highlight" in out["tags"]
    assert "ball-in-play" in out["tags"]
    assert out["summary"]


def test_fallback_no_ball_omits_ball_tag():
    out = fallback(_moment(ball_present=False, peak_person_count=1, score=0.5))
    assert "ball-in-play" not in out["tags"]
