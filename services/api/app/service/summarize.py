"""Prompt construction + templated fallback for moment summaries.

Kept separate from analyze.py so the prompt/fallback logic is unit-testable
without the pipeline, and so analyze.py stays under the 300-line limit.
"""

from app.types import Moment, Video


def build_prompt(moment: Moment, video: Video) -> str:
    """Build a text-only prompt from detection/track metadata (no vision)."""
    lines = [
        f"Sports clip: {video.filename}",
        f"Moment window: {moment.start_s:.1f}s-{moment.end_s:.1f}s "
        f"({moment.duration_s:.1f}s long)",
        f"Peak intensity score: {moment.score:.2f}",
        f"People on screen at peak: {moment.peak_person_count}",
        f"Distinct tracked players (ByteTrack): {moment.unique_track_ids}",
        f"Sports ball detected: {'yes' if moment.ball_present else 'no'}",
        f"Total detections in window: {moment.detection_count}",
    ]
    return "\n".join(lines)


def fallback(moment: Moment) -> dict:
    """Templated description used when the LLM is unavailable."""
    ball = "with the ball in play" if moment.ball_present else "in open play"
    desc = (
        f"High-activity moment at {moment.start_s:.0f}s lasting "
        f"{moment.duration_s:.0f}s, with {moment.peak_person_count} players "
        f"and {moment.unique_track_ids} distinct tracks {ball}. "
        "Configure ANTHROPIC_API_KEY for an AI-written summary."
    )
    tags = ["highlight"]
    if moment.ball_present:
        tags.append("ball-in-play")
    if moment.peak_person_count >= 4:
        tags.append("crowded")
    if moment.score >= 0.75:
        tags.append("high-intensity")
    return {
        "summary": f"Action at {moment.start_s:.0f}s",
        "description": desc,
        "tags": tags,
    }
