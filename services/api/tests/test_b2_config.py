"""Tests for B2 standards required by quality-keeper."""

import logging

import pytest
from pydantic import ValidationError

import main
from app.config import Settings
from app.repo import b2_client


class FakeS3Client:
    def __init__(self):
        self.put_calls = []

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)


def _set_required_b2_settings(monkeypatch):
    monkeypatch.setattr(main.settings, "b2_application_key_id", "key-id")
    monkeypatch.setattr(main.settings, "b2_application_key", "key")
    monkeypatch.setattr(main.settings, "b2_bucket_name", "bucket")
    monkeypatch.setattr(main.settings, "b2_region", "us-west-004")


def test_s3_endpoint_is_derived_from_region():
    settings = Settings(b2_region="us-east-001")

    assert settings.b2_s3_endpoint_url == "https://s3.us-east-001.backblazeb2.com"


@pytest.mark.parametrize(
    "region",
    [
        "us-west-004.evil",
        "us-west-004/evil",
        "us-west-004@evil",
        "us-west-004?evil",
        "us-west-004#evil",
        "us-west-004:443",
    ],
)
def test_s3_endpoint_rejects_malformed_region(region):
    with pytest.raises(ValidationError, match="B2_REGION"):
        Settings(b2_region=region)


def test_b2_region_has_no_default():
    settings = Settings(_env_file=None)

    assert settings.b2_region == ""


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


def test_s3_client_rejects_malformed_region_before_boto3(monkeypatch):
    def fake_client(*_args, **_kwargs):
        pytest.fail("boto3.client should not be called")

    monkeypatch.setattr(b2_client.boto3, "client", fake_client)
    monkeypatch.setattr(b2_client.settings, "b2_region", "us-west-004@evil")
    monkeypatch.setattr(b2_client.settings, "b2_application_key_id", "key-id")
    monkeypatch.setattr(b2_client.settings, "b2_application_key", "key")
    b2_client.get_s3_client.cache_clear()

    try:
        with pytest.raises(ValueError, match="B2_REGION"):
            b2_client.get_s3_client()
    finally:
        b2_client.get_s3_client.cache_clear()


def test_upload_metadata_url_is_none_without_public_base(monkeypatch):
    fake_client = FakeS3Client()
    monkeypatch.setattr(b2_client, "get_s3_client", lambda: fake_client)
    monkeypatch.setattr(b2_client.settings, "b2_bucket_name", "bucket")
    monkeypatch.setattr(b2_client.settings, "b2_public_url_base", "")

    metadata = b2_client.upload_file(
        b"video", "clips/moment 1.mp4", "video/mp4"
    )

    assert metadata.url is None
    assert fake_client.put_calls[0]["Bucket"] == "bucket"


def test_upload_metadata_url_uses_optional_public_base(monkeypatch):
    fake_client = FakeS3Client()
    monkeypatch.setattr(b2_client, "get_s3_client", lambda: fake_client)
    monkeypatch.setattr(b2_client.settings, "b2_bucket_name", "bucket")
    monkeypatch.setattr(
        b2_client.settings,
        "b2_public_url_base",
        " https://bucket.s3.us-west-004.backblazeb2.com/ ",
    )

    metadata = b2_client.upload_file(
        b"video", "clips/moment 1.mp4", "video/mp4"
    )

    assert metadata.url == (
        "https://bucket.s3.us-west-004.backblazeb2.com/clips/moment%201.mp4"
    )


@pytest.mark.asyncio
async def test_lifespan_allows_private_bucket_without_public_url(monkeypatch):
    _set_required_b2_settings(monkeypatch)
    monkeypatch.setattr(main.settings, "b2_public_url_base", "")

    async with main.lifespan(None):
        pass


@pytest.mark.asyncio
async def test_lifespan_requires_region(monkeypatch):
    _set_required_b2_settings(monkeypatch)
    monkeypatch.setattr(main.settings, "b2_region", "")
    monkeypatch.setattr(main.settings, "b2_public_url_base", "")

    with pytest.raises(RuntimeError, match="B2_REGION"):
        async with main.lifespan(None):
            pass


@pytest.mark.asyncio
async def test_lifespan_rejects_malformed_region(monkeypatch):
    _set_required_b2_settings(monkeypatch)
    monkeypatch.setattr(main.settings, "b2_region", "us-west-004/evil")
    monkeypatch.setattr(main.settings, "b2_public_url_base", "")

    with pytest.raises(RuntimeError, match="B2_REGION"):
        async with main.lifespan(None):
            pass


@pytest.mark.asyncio
async def test_lifespan_rejects_insecure_public_url(monkeypatch):
    _set_required_b2_settings(monkeypatch)
    monkeypatch.setattr(main.settings, "b2_public_url_base", "http://bucket.test")

    with pytest.raises(RuntimeError, match="B2_PUBLIC_URL_BASE must be an HTTPS URL"):
        async with main.lifespan(None):
            pass


@pytest.mark.asyncio
async def test_lifespan_warns_when_public_url_is_set(monkeypatch, caplog):
    _set_required_b2_settings(monkeypatch)
    monkeypatch.setattr(
        main.settings,
        "b2_public_url_base",
        "https://bucket.s3.us-west-004.backblazeb2.com",
    )

    with caplog.at_level(logging.WARNING, logger="api"):
        async with main.lifespan(None):
            pass

    assert "intentionally public B2 buckets" in caplog.text
