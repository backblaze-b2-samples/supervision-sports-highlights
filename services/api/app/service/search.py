"""Moment search across every analyzed video's manifest.

The manifest.json per video doubles as the search index — each moment carries
its Claude (or templated) description and tags. Search is a case-insensitive
substring/token match over summary + description + tags. No external search
engine; this is a sample, and the corpus is small.
"""

import logging

from app.repo import video_store as store
from app.types import SearchHit

logger = logging.getLogger(__name__)


def search(query: str, limit: int = 50) -> list[SearchHit]:
    q = query.strip().lower()
    if not q:
        return []
    tokens = [t for t in q.split() if t]

    hits: list[tuple[float, SearchHit]] = []
    for vid in store.list_video_ids():
        video = store.read_manifest(vid)
        if video is None:
            continue
        for moment in video.moments:
            score = _score(moment, q, tokens)
            if score > 0:
                hits.append(
                    (
                        score,
                        SearchHit(
                            video_id=video.id,
                            video_filename=video.filename,
                            moment=moment,
                        ),
                    )
                )

    hits.sort(key=lambda t: (t[0], t[1].moment.score), reverse=True)
    return [hit for _, hit in hits[:limit]]


def _score(moment, q: str, tokens: list[str]) -> float:
    haystack = " ".join(
        [moment.summary, moment.description, " ".join(moment.tags)]
    ).lower()
    if not haystack.strip():
        return 0.0
    # Exact phrase match ranks highest; otherwise count token hits.
    if q in haystack:
        return 2.0 + moment.score
    matched = sum(1 for tok in tokens if tok in haystack)
    if matched == 0:
        return 0.0
    return matched / len(tokens)
