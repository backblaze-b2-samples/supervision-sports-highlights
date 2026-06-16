"""Roboflow Supervision adapter — multi-object tracking + annotation.

This is the showcase: detections (from `repo.detection`) are fed through
`sv.ByteTrack` for persistent IDs, then drawn with Box/Label/Trace annotators.
`supervision` is imported lazily so the module stays importable without the
CV runtime installed (structural tests).
"""


def new_tracker():
    """Return a fresh ByteTrack tracker (one per video)."""
    import supervision as sv

    return sv.ByteTrack()


def new_annotators():
    """Return (box, label, trace) annotators with sensible defaults."""
    import supervision as sv

    box = sv.BoxAnnotator(thickness=2)
    label = sv.LabelAnnotator(text_scale=0.5, text_thickness=1)
    trace = sv.TraceAnnotator(thickness=2, trace_length=30)
    return box, label, trace


def track(tracker, detections):
    """Advance the tracker with this frame's detections; returns tracked
    detections carrying `tracker_id`."""
    return tracker.update_with_detections(detections)


def annotate_frame(frame, detections, annotators):
    """Draw boxes, labels (class + track id), and motion traces onto a copy
    of `frame`. Returns the annotated frame (numpy array)."""
    box, label, trace = annotators
    labels = _labels(detections)
    out = frame.copy()
    out = trace.annotate(scene=out, detections=detections)
    out = box.annotate(scene=out, detections=detections)
    out = label.annotate(scene=out, detections=detections, labels=labels)
    return out


def _labels(detections) -> list[str]:
    """Label each box with its model-reported class name + track id. Uses the
    `class_name` strings `from_inference` attaches, so labels are correct
    regardless of the model's class-id base (COCO-80 vs COCO-91)."""
    from app.repo import detection as det

    labels: list[str] = []
    n = len(detections)
    names = det.class_names_of(detections)
    track_ids = (
        detections.tracker_id if detections.tracker_id is not None else [None] * n
    )
    for name, tid in zip(names, track_ids, strict=False):
        label = name or "object"
        labels.append(f"#{int(tid)} {label}" if tid is not None else label)
    return labels
