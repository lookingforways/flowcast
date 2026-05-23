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
