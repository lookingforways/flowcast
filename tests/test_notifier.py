"""Tests for webhook notifier."""
import asyncio
import hashlib
import hmac
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_async_client_mock(raise_exc=None):
    """Return a mock httpx.AsyncClient context manager."""
    response = MagicMock()
    response.raise_for_status = MagicMock(side_effect=raise_exc)

    client = AsyncMock()
    client.post = AsyncMock(return_value=response)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_notify_skips_when_no_url():
    """notify() makes no HTTP call when WEBHOOK_URL is empty."""
    from app.services.notifier import notify

    with patch("app.services.notifier.settings") as mock_settings, \
         patch("httpx.AsyncClient") as mock_client_cls:
        mock_settings.webhook_url = ""
        mock_settings.webhook_secret = ""
        mock_settings.webhook_timeout = 10.0

        _run(notify("publish_success", {"episode": "Test"}))

        mock_client_cls.assert_not_called()


def test_notify_validates_url_before_request():
    """notify() stops early when validate_external_url raises ValueError."""
    from app.services.notifier import notify

    with patch("app.services.notifier.settings") as mock_settings, \
         patch("app.services.notifier.validate_external_url", side_effect=ValueError("private IP")) as mock_validate, \
         patch("httpx.AsyncClient") as mock_client_cls:
        mock_settings.webhook_url = "http://192.168.1.1/hook"
        mock_settings.webhook_secret = ""
        mock_settings.webhook_timeout = 10.0

        _run(notify("download_error", {"episode": "Test", "error": "oops"}))

        mock_validate.assert_called_once_with("http://192.168.1.1/hook")
        mock_client_cls.assert_not_called()


def test_notify_sends_correct_json_payload():
    """notify() sends event, timestamp, and all payload fields as JSON."""
    from app.services.notifier import notify

    mock_client = _make_async_client_mock()

    with patch("app.services.notifier.settings") as mock_settings, \
         patch("app.services.notifier.validate_external_url"), \
         patch("app.services.notifier._SSRFSafeTransport"), \
         patch("httpx.AsyncClient", return_value=mock_client):
        mock_settings.webhook_url = "https://example.com/hook"
        mock_settings.webhook_secret = ""
        mock_settings.webhook_timeout = 10.0

        _run(notify("publish_success", {
            "podcast": "Mi Podcast",
            "episode": "Ep 1",
            "youtube_url": "https://youtu.be/abc",
        }))

    call_kwargs = mock_client.post.call_args
    body = json.loads(call_kwargs.kwargs["content"])

    assert body["event"] == "publish_success"
    assert "timestamp" in body
    assert body["podcast"] == "Mi Podcast"
    assert body["episode"] == "Ep 1"
    assert body["youtube_url"] == "https://youtu.be/abc"


def test_notify_adds_hmac_header():
    """notify() adds X-FlowCast-Signature header when WEBHOOK_SECRET is set."""
    from app.services.notifier import notify

    mock_client = _make_async_client_mock()
    secret = "super-secret"

    with patch("app.services.notifier.settings") as mock_settings, \
         patch("app.services.notifier.validate_external_url"), \
         patch("app.services.notifier._SSRFSafeTransport"), \
         patch("httpx.AsyncClient", return_value=mock_client):
        mock_settings.webhook_url = "https://example.com/hook"
        mock_settings.webhook_secret = secret
        mock_settings.webhook_timeout = 10.0

        _run(notify("render_error", {"episode": "Ep 2", "error": "FFmpeg died"}))

    call_kwargs = mock_client.post.call_args
    headers = call_kwargs.kwargs["headers"]
    raw_body = call_kwargs.kwargs["content"]

    assert "X-FlowCast-Signature" in headers
    expected_sig = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    assert headers["X-FlowCast-Signature"] == f"sha256={expected_sig}"


def test_notify_does_not_raise_on_http_error():
    """notify() logs and returns normally when the webhook endpoint returns an error."""
    import httpx
    from app.services.notifier import notify

    mock_client = _make_async_client_mock(
        raise_exc=httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock())
    )

    with patch("app.services.notifier.settings") as mock_settings, \
         patch("app.services.notifier.validate_external_url"), \
         patch("app.services.notifier._SSRFSafeTransport"), \
         patch("httpx.AsyncClient", return_value=mock_client):
        mock_settings.webhook_url = "https://example.com/hook"
        mock_settings.webhook_secret = ""
        mock_settings.webhook_timeout = 10.0

        # Must not raise
        _run(notify("publish_error", {"episode": "Ep 3", "error": "upload failed"}))
