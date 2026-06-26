"""Tests for B2 standards required by quality-keeper."""

from app.config import Settings
from app.repo import b2_client


def test_s3_endpoint_is_derived_from_region():
    settings = Settings(b2_region="us-east-001")

    assert settings.b2_s3_endpoint_url == "https://s3.us-east-001.backblazeb2.com"


def test_s3_client_uses_derived_endpoint_and_custom_user_agent(monkeypatch):
    captured = {}

    def fake_client(service_name, **kwargs):
        captured["service_name"] = service_name
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(b2_client.boto3, "client", fake_client)
    monkeypatch.setattr(b2_client.settings, "b2_region", "us-west-004")
    monkeypatch.setattr(b2_client.settings, "b2_application_key_id", "key-id")
    monkeypatch.setattr(b2_client.settings, "b2_application_key", "key")
    b2_client.get_s3_client.cache_clear()

    try:
        b2_client.get_s3_client()

        assert captured["service_name"] == "s3"
        assert captured["endpoint_url"] == "https://s3.us-west-004.backblazeb2.com"
        assert captured["region_name"] == "us-west-004"
        assert captured["config"].user_agent_extra == b2_client.B2_USER_AGENT
        assert "backblaze-b2-samples" in captured["config"].user_agent_extra
    finally:
        b2_client.get_s3_client.cache_clear()


def test_public_url_uses_standard_base_var(monkeypatch):
    monkeypatch.setattr(
        b2_client.settings,
        "b2_public_url_base",
        "https://bucket.s3.us-west-004.backblazeb2.com/",
    )

    assert (
        b2_client._public_url("clips/moment 1.mp4")
        == "https://bucket.s3.us-west-004.backblazeb2.com/clips/moment%201.mp4"
    )
