"""OpenCV-backed frame loop: decode → detect+track → annotated render.

OpenCV (`cv2`, installed transitively by the `inference` runtime) is an
external dependency, so per the repo invariant it lives here, not in the
service layer. This module wires together `detection`, `annotate`, and
`media`, and hands the service layer plain per-frame stats it can reason about
without importing any CV library.

Everything is imported lazily so the module stays importable for structural
tests without the CV runtime installed.
"""

import logging
import os

from app.repo import annotate, detection
from app.repo.media import encode_from_frames

logger = logging.getLogger(__name__)


def analyze_and_annotate(
    src_path: str,
    frames_dir: str,
    annotated_path: str,
    *,
    stride: int,
    on_stat,
):
    """Decode the video, run detection+tracking every `stride` frames, render
    an annotated frame for EVERY frame (carrying forward the latest tracked
    detections so output looks full-FPS), and encode the annotated mp4.

    `on_stat(t, frame_stat)` is called once per analyzed frame with a plain
    dict (no CV types leak to the service): keys `person_count`,
    `ball_present`, `motion`, `track_ids` (list[int]), `detection_count`.
    Returns the source fps.
    """
    import cv2
    import numpy as np

    cap = cv2.VideoCapture(src_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {src_path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0

    tracker = annotate.new_tracker()
    annotators = annotate.new_annotators()
    os.makedirs(frames_dir, exist_ok=True)

    prev_gray = None
    last_detections = None
    idx = 0
    written = 0
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            t = idx / fps

            if idx % stride == 0:
                dets = detection.infer_frame(frame)
                tracked = annotate.track(tracker, dets)
                last_detections = tracked

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                motion = _motion(prev_gray, gray, np)
                prev_gray = gray
                on_stat(t, _to_stat(tracked, motion))

            # Annotate every frame using the most recent tracked detections.
            if last_detections is not None:
                out = annotate.annotate_frame(frame, last_detections, annotators)
            else:
                out = frame
            cv2.imwrite(f"{frames_dir}/frame-{written:06d}.jpg", out)
            written += 1
            idx += 1
    finally:
        cap.release()

    if written > 0:
        encode_from_frames(frames_dir, "frame-%06d.jpg", fps, annotated_path)
    return fps


def _to_stat(tracked, motion: float) -> dict:
    """Reduce an sv.Detections to plain primitives for the service layer."""
    tracker_id = tracked.tracker_id
    n = len(tracked)
    names = detection.class_names_of(tracked)
    person_count = sum(1 for name in names if detection.is_person(name))
    ball_present = any(detection.is_ball(name) for name in names)
    track_ids = [int(t) for t in tracker_id] if tracker_id is not None else []
    return {
        "person_count": person_count,
        "ball_present": ball_present,
        "motion": motion,
        "track_ids": track_ids,
        "detection_count": n,
    }


def _motion(prev_gray, gray, np) -> float:
    """Normalized mean absolute inter-frame difference, ~0..1."""
    if prev_gray is None or prev_gray.shape != gray.shape:
        return 0.0
    diff = np.abs(gray.astype("float32") - prev_gray.astype("float32"))
    return float(min(1.0, (diff.mean() / 255.0) * 6.0))
