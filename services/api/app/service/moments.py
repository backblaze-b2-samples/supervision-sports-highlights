"""Sport-agnostic moment-detection heuristic.

Per analyzed frame we compute an intensity score from tracked-person count,
sports-ball presence, and frame-to-frame motion. A *moment* is a contiguous
run of frames above a rolling threshold; near-adjacent runs are merged, then
ranked and capped to the top-N. No CV libraries here — this operates on the
per-frame stats the analyze orchestrator already collected, so it stays a
pure, unit-testable function.
"""

from dataclasses import dataclass, field


@dataclass
class FrameStat:
    """One analyzed frame's stats, produced by the detect+track loop."""

    t: float  # timestamp in seconds
    person_count: int = 0
    ball_present: bool = False
    motion: float = 0.0  # 0..1 normalized inter-frame motion
    track_ids: set[int] = field(default_factory=set)
    detection_count: int = 0


@dataclass
class DetectedMoment:
    start_s: float
    end_s: float
    score: float
    peak_person_count: int
    unique_track_ids: int
    ball_present: bool
    detection_count: int
    peak_t: float  # timestamp of peak intensity (for the thumbnail)


def _intensity(stat: FrameStat) -> float:
    """Heuristic intensity in roughly 0..1. People drive the floor, the ball
    and motion add the spikes that mark real action."""
    people = min(stat.person_count, 10) / 10.0
    ball = 0.25 if stat.ball_present else 0.0
    return min(1.0, 0.45 * people + ball + 0.5 * stat.motion)


def detect_moments(
    stats: list[FrameStat],
    *,
    max_moments: int,
    min_gap_s: float = 1.5,
    min_duration_s: float = 1.0,
    pad_s: float = 0.75,
) -> list[DetectedMoment]:
    """Find, merge, rank, and cap highlight moments."""
    if not stats:
        return []

    scores = [_intensity(s) for s in stats]
    mean = sum(scores) / len(scores)
    peak = max(scores)
    # Rolling threshold: a high-water mark between the clip's average and its
    # busiest moment, so it adapts to the footage's own dynamic range instead
    # of assuming a crowded frame. A fixed additive offset (e.g. mean + 0.15)
    # overshoots the peak on uniform footage -- a couple of tracked players and
    # a sparsely-detected ball keep intensity in a narrow ~0.1-0.4 band, so the
    # peak never clears mean + 0.15. Scaling by (peak - mean) fires on the most
    # active stretch in any footage; the small absolute floor only suppresses a
    # literally-empty field (near-zero scores throughout).
    threshold = max(mean + 0.45 * (peak - mean), 0.1)

    runs: list[tuple[int, int]] = []
    start: int | None = None
    for i, sc in enumerate(scores):
        if sc >= threshold and start is None:
            start = i
        elif sc < threshold and start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(scores) - 1))

    moments = [_build(stats, scores, a, b, pad_s) for a, b in runs]
    moments = [m for m in moments if m.end_s - m.start_s >= min_duration_s]
    moments = _merge(moments, min_gap_s)

    moments.sort(key=lambda m: m.score, reverse=True)
    return moments[:max_moments]


def _build(stats, scores, a: int, b: int, pad_s: float) -> DetectedMoment:
    window = stats[a : b + 1]
    win_scores = scores[a : b + 1]
    peak_idx = a + max(range(len(win_scores)), key=lambda i: win_scores[i])
    track_ids: set[int] = set()
    for s in window:
        track_ids |= s.track_ids
    return DetectedMoment(
        start_s=max(0.0, window[0].t - pad_s),
        end_s=window[-1].t + pad_s,
        score=round(max(win_scores), 4),
        peak_person_count=max((s.person_count for s in window), default=0),
        unique_track_ids=len(track_ids),
        ball_present=any(s.ball_present for s in window),
        detection_count=sum(s.detection_count for s in window),
        peak_t=stats[peak_idx].t,
    )


def _merge(moments: list[DetectedMoment], min_gap_s: float) -> list[DetectedMoment]:
    """Merge moments whose gap is smaller than min_gap_s."""
    if not moments:
        return []
    moments = sorted(moments, key=lambda m: m.start_s)
    merged = [moments[0]]
    for m in moments[1:]:
        last = merged[-1]
        if m.start_s - last.end_s <= min_gap_s:
            merged[-1] = DetectedMoment(
                start_s=last.start_s,
                end_s=max(last.end_s, m.end_s),
                score=max(last.score, m.score),
                peak_person_count=max(last.peak_person_count, m.peak_person_count),
                unique_track_ids=max(last.unique_track_ids, m.unique_track_ids),
                ball_present=last.ball_present or m.ball_present,
                detection_count=last.detection_count + m.detection_count,
                peak_t=last.peak_t if last.score >= m.score else m.peak_t,
            )
        else:
            merged.append(m)
    return merged
