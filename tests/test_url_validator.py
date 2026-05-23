"""Tests for SSRF protection in url_validator.py."""
import pytest
from app.utils.url_validator import validate_external_url


def test_valid_url_passes():
    assert validate_external_url("https://example.com/feed.rss") == "https://example.com/feed.rss"


def test_valid_http_passes():
    assert validate_external_url("http://example.com/feed.xml")


def test_loopback_ipv4_blocked():
    # IP literals are wrapped with "Invalid or disallowed IP literal"
    with pytest.raises(ValueError, match="disallowed IP literal"):
        validate_external_url("http://127.0.0.1/secret")


def test_loopback_localhost_blocked():
    # Hostnames propagate the original message
    with pytest.raises(ValueError, match="loopback"):
        validate_external_url("http://localhost/secret")


def test_private_class_a_blocked():
    with pytest.raises(ValueError, match="disallowed IP literal"):
        validate_external_url("http://10.0.0.1/")


def test_private_class_b_blocked():
    with pytest.raises(ValueError, match="disallowed IP literal"):
        validate_external_url("http://172.16.0.1/")


def test_private_class_c_blocked():
    with pytest.raises(ValueError, match="disallowed IP literal"):
        validate_external_url("http://192.168.1.1/")


def test_cgnat_blocked():
    with pytest.raises(ValueError, match="disallowed IP literal"):
        validate_external_url("http://100.64.0.1/")


def test_ipv6_loopback_blocked():
    with pytest.raises(ValueError, match="loopback"):
        validate_external_url("http://[::1]/")


def test_ipv4_mapped_ipv6_blocked():
    with pytest.raises(ValueError):
        validate_external_url("http://[::ffff:127.0.0.1]/")


def test_octal_ip_blocked():
    with pytest.raises(ValueError):
        validate_external_url("http://0177.0.0.1/")


def test_ftp_scheme_blocked():
    with pytest.raises(ValueError, match="scheme"):
        validate_external_url("ftp://example.com/file.mp3")


def test_file_scheme_blocked():
    with pytest.raises(ValueError, match="scheme"):
        validate_external_url("file:///etc/passwd")


def test_empty_url_blocked():
    with pytest.raises(ValueError):
        validate_external_url("")


def test_no_hostname_blocked():
    with pytest.raises(ValueError):
        validate_external_url("https:///path")


# ── M-05: DNS TOCTOU — connect-time IP validation ────────────────────────────

def test_check_ip_str_blocks_private():
    from app.utils.url_validator import _check_ip_str
    with pytest.raises(ValueError, match="private"):
        _check_ip_str("192.168.1.1")


def test_check_ip_str_blocks_loopback():
    from app.utils.url_validator import _check_ip_str
    with pytest.raises(ValueError, match="loopback"):
        _check_ip_str("127.0.0.1")


def test_safe_http_connection_blocks_private_ip():
    """_SafeHTTPConnection must reject private IPs at connect() time (DNS TOCTOU gap)."""
    import socket
    from unittest.mock import patch
    from app.services.rss import _SafeHTTPConnection

    conn = _SafeHTTPConnection("example.com", 80)
    fake = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.100", 80))]
    with patch("app.services.rss.socket.getaddrinfo", return_value=fake):
        with pytest.raises(ValueError, match="private"):
            conn.connect()


def test_safe_https_connection_blocks_private_ip():
    """_SafeHTTPSConnection must reject private IPs at connect() time (DNS TOCTOU gap)."""
    import socket
    from unittest.mock import patch
    from app.services.rss import _SafeHTTPSConnection

    conn = _SafeHTTPSConnection("example.com", 443)
    fake = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443))]
    with patch("app.services.rss.socket.getaddrinfo", return_value=fake):
        with pytest.raises(ValueError, match="private"):
            conn.connect()


def test_ssrf_safe_transport_blocks_private_ip():
    """_SSRFSafeTransport must reject private IPs resolved at handle_async_request time."""
    import asyncio
    import socket
    import httpx
    from unittest.mock import patch
    from app.utils.url_validator import _SSRFSafeTransport

    transport = _SSRFSafeTransport()
    fake = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.1", 443))]

    async def _run():
        request = httpx.Request("GET", "https://example.com/")
        with patch("app.utils.url_validator.socket.getaddrinfo", return_value=fake):
            await transport.handle_async_request(request)

    with pytest.raises(ValueError, match="private"):
        asyncio.run(_run())
