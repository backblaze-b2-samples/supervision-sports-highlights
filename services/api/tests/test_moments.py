"""Unit tests for the sport-agnostic moment-detection heuristic."""

from app.service.moments import FrameStat, detect_moments


def _quiet(t: float) -> FrameStat:
    return FrameStat(t=t, person_count=1, ball_present=False, motion=0.02)


def _action(t: float, tid: int) -> FrameStat:
    return FrameStat(
        t=t,
        person_count=6,
        ball_present=True,
        motion=0.6,
        track_ids={tid, tid + 1},
        detection_count=7,
    )


def test_empty_input_returns_no_moments():
    assert detect_moments([], max_moments=8) == []


def test_detects_a_burst_of_action():
    stats = [_quiet(i * 0.5) for i in range(10)]
    # A clear action burst in the middle.
    stats += [_action(5.0 + i * 0.5, tid=i) for i in range(6)]
    stats += [_quiet(8.0 + i * 0.5) for i in range(10)]

    moments = detect_moments(stats, max_moments=8)
    assert len(moments) >= 1
    m = moments[0]
    assert m.ball_present is True
    assert m.peak_person_count >= 4
    assert m.unique_track_ids >= 1
    # The window should overlap the action region (~5s-7.5s) with padding.
    assert m.start_s < 8.0 and m.end_s > 5.0


def test_caps_to_max_moments():
    stats = []
    t = 0.0
    # Ten well-separated action bursts.
    for burst in range(10):
        for i in range(4):
            stats.append(_action(t, tid=burst * 10 + i))
            t += 0.4
        for _ in range(6):  # quiet gap
            stats.append(_quiet(t))
            t += 0.5

    moments = detect_moments(stats, max_moments=3)
    assert len(moments) == 3
    # Ranked by score, descending.
    assert moments[0].score >= moments[1].score >= moments[2].score
