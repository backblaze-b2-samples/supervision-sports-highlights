"""Roboflow Inference adapter — the ONLY place the detection model runs.

Pre-trained COCO models (default `rfdetr-base`) run locally with NO API key;
weights auto-download on first use. `ROBOFLOW_API_KEY` is optional and unlocks
Roboflow Universe sport-specific models + hosted serverless inference.

Detections are returned as Supervision `sv.Detections` (via
`sv.Detections.from_inference`) so the rest of the pipeline is decoupled from
the raw inference response shape. `inference`/`supervision` are heavy imports,
so they are imported lazily inside the functions (keeps the module importable
for structural tests without the CV runtime installed).
"""

import functools
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Class *names* relevant to ball sports, mapped to the heuristic's two
# semantic roles. We key off names rather than integer ids because the id base
# differs by model: COCO-80 (0-indexed, e.g. YOLO) vs COCO-91 (1-indexed, e.g.
# the default keyless `rfdetr-base`, where person=1 and sports ball=37).
# `sv.Detections.from_inference` always populates `data["class_name"]`, so name
# matching is model-agnostic. The accepted names are configurable so Roboflow
# Universe models with custom labels (e.g. "player"/"basketball") can drive the
# heuristic; the keyless COCO default ("person"/"sports ball") is unchanged.


def is_person(name: str | None) -> bool:
    """True if a (lower-cased) class name maps to the heuristic's person role."""
    return name is not None and name in settings.person_class_set


def is_ball(name: str | None) -> bool:
    """True if a (lower-cased) class name maps to the heuristic's ball role."""
    return name is not None and name in settings.ball_class_set


@functools.lru_cache(maxsize=1)
def _get_model():
    """Load the detection model once (weights auto-download on first call)."""
    from inference import get_model

    kwargs: dict = {"model_id": settings.detection_model}
    if settings.roboflow_api_key:
        kwargs["api_key"] = settings.roboflow_api_key
    logger.info("Loading detection model: %s", settings.detection_model)
    return get_model(**kwargs)


def infer_frame(frame):
    """Run detection on a single BGR frame (numpy array, as decoded by
    OpenCV) and return an `sv.Detections`.

    `frame` is passed positionally so this works with any model returned by
    `get_model`. `model.infer()` returns a list of responses (one per image).
    """
    import supervision as sv

    model = _get_model()
    results = model.infer(frame)[0]
    return sv.Detections.from_inference(results)


def class_names_of(detections) -> list[str | None]:
    """Per-detection class-name strings (lower-cased) for an `sv.Detections`.

    `from_inference` stores them under `data["class_name"]`. Returns one entry
    per detection (`None` where unavailable) so callers can match on semantic
    names instead of model-specific integer ids. Keeps CV-type access in repo/.
    """
    names = detections.data.get("class_name") if detections.data else None
    if names is None:
        return [None] * len(detections)
    return [str(n).lower() if n is not None else None for n in names]
