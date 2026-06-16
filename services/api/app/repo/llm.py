"""Anthropic Claude adapter for moment summaries.

Text-only: the prompt is built from detection/track metadata, so summaries are
cheap (~$0.03-0.05 / full demo run) and require no vision. Graceful
degradation: `is_available()` is False when `ANTHROPIC_API_KEY` is absent, and
the service layer falls back to a templated description.

`anthropic` is imported lazily so the module stays importable without the SDK.
"""

import functools
import logging

from app.config import settings

logger = logging.getLogger(__name__)


def is_available() -> bool:
    return bool(settings.anthropic_api_key)


@functools.lru_cache(maxsize=1)
def _client():
    import anthropic

    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


_SYSTEM = (
    "You are a sports analyst writing concise highlight captions. "
    "Given object-detection and tracking stats for a moment in a sports clip, "
    "write a vivid one- or two-sentence caption of the likely on-field action, "
    "then up to five short lowercase search tags. The detector is generic "
    "(COCO: people + sports ball), so describe action plausibly without "
    "inventing specific player names or scores."
)


def summarize_moment(prompt: str) -> dict:
    """Call Claude and return {summary, description, tags}. Raises on failure;
    the caller decides whether to fall back."""
    msg = _client().messages.create(
        model=settings.summary_model,
        max_tokens=300,
        system=_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": (
                    prompt
                    + "\n\nRespond as JSON with keys: summary (string), "
                    "description (string, 1-2 sentences), tags (array of "
                    "<=5 lowercase strings)."
                ),
            }
        ],
    )
    text = "".join(block.text for block in msg.content if block.type == "text")
    return _parse(text)


def _parse(text: str) -> dict:
    import json

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        try:
            data = json.loads(text[start : end + 1])
            return {
                "summary": str(data.get("summary", "")).strip(),
                "description": str(data.get("description", "")).strip(),
                "tags": [str(t).strip().lower() for t in data.get("tags", [])][:5],
            }
        except (ValueError, TypeError):
            logger.warning("Could not parse Claude JSON; using raw text")
    cleaned = text.strip()
    return {"summary": cleaned[:80], "description": cleaned, "tags": []}
