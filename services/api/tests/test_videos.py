"""Tests for video registration, scoped delete, and search over manifests."""

from datetime import UTC, datetime

import pytest

from app.service import search as search_service
from app.service import videos as videos_service
from app.types import Moment, Video, VideoStatus


def _video(vid: str, moments=None) -> Video:
    now = datetime.now(UTC)
    return Video(
        id=vid,
        filename=f"{vid}.mp4",
        status=VideoStatus.READY,
        source_key=f"prefix/videos/{vid}/source.mp4",
        moments=moments or [],
        moment_count=len(moments or []),
        created_at=now,
        updated_at=now,
    )


def test_register_rejects_non_video_type():
    with pytest.raises(videos_service.VideoError) as exc:
        videos_service.register_upload(b"data", "x.txt", "text/plain")
    assert exc.value.status_code == 415


def test_register_rejects_empty():
    with pytest.raises(videos_service.VideoError):
        videos_service.register_upload(b"", "x.mp4", "video/mp4")


def test_register_stores_source_and_manifest(monkeypatch):
    puts: list[str] = []
    manifests: list[Video] = []
    monkeypatch.setattr(
        videos_service.store, "put_bytes",
        lambda key, data, ct: puts.append(key),
    )
    monkeypatch.setattr(
        videos_service.store, "write_manifest",
        lambda v: manifests.append(v),
    )

    video = videos_service.register_upload(b"\x00\x01", "game.mp4", "video/mp4")
    assert video.status == VideoStatus.UPLOADED
    assert any(k.endswith("source.mp4") for k in puts)
    assert manifests and manifests[0].id == video.id


def test_invalid_video_id_rejected():
    with pytest.raises(videos_service.VideoError):
        videos_service.get_video("not-a-valid-id")


def test_delete_is_scoped_to_video_prefix(monkeypatch):
    vid = "b" * 32
    deleted_prefixes: list[str] = []
    monkeypatch.setattr(
        videos_service.store, "read_manifest", lambda v: _video(v)
    )

    def fake_delete(video_id):
        deleted_prefixes.append(video_id)
        return 5

    monkeypatch.setattr(
        videos_service.store, "delete_video_prefix", fake_delete
    )
    count = videos_service.delete_video(vid)
    assert count == 5
    # Only the requested video's id is ever passed to the scoped delete.
    assert deleted_prefixes == [vid]


def test_delete_missing_video_raises(monkeypatch):
    monkeypatch.setattr(videos_service.store, "read_manifest", lambda v: None)
    with pytest.raises(videos_service.VideoNotFound):
        videos_service.delete_video("c" * 32)


def test_search_matches_tags_and_description(monkeypatch):
    vid_a = "a" * 32
    vid_b = "d" * 32
    m1 = Moment(
        id=0, start_s=1, end_s=3, score=0.9,
        description="A fast counter-attack down the wing", tags=["counter", "wing"],
    )
    m2 = Moment(
        id=0, start_s=1, end_s=3, score=0.5,
        description="A slow buildup in midfield", tags=["buildup"],
    )
    store = {vid_a: _video(vid_a, [m1]), vid_b: _video(vid_b, [m2])}

    monkeypatch.setattr(search_service.store, "list_video_ids", lambda: list(store))
    monkeypatch.setattr(search_service.store, "read_manifest", lambda v: store[v])

    hits = search_service.search("counter")
    assert len(hits) == 1
    assert hits[0].video_id == vid_a
    assert hits[0].moment.id == 0


def test_search_empty_query_returns_nothing():
    assert search_service.search("   ") == []
