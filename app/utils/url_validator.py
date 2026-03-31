"""SSRF protection: validate URLs before making outbound HTTP requests."""
from __future__ import annotations

import ipaddress
from urllib.parse import urlparse


def validate_external_url(url: str) -> str:
    """Validate that a URL is safe to fetch externally.

    Raises ValueError if:
    - The scheme is not http or https
    - The host is a private, loopback, link-local, or reserved IP address

    Returns the original URL string unchanged if valid.
    """
    if not url:
        raise ValueError("URL cannot be empty")

    parsed = urlparse(url)

    if parsed.scheme not in ("http", "https"):
        raise ValueError(
            f"URL scheme must be http or https, got: {parsed.scheme!r}"
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL has no hostname")

    # If the host is a literal IP address, block private/reserved ranges
    try:
        addr = ipaddress.ip_address(hostname)
        if addr.is_loopback:
            raise ValueError(f"URL targets a loopback address: {hostname}")
        if addr.is_private:
            raise ValueError(f"URL targets a private IP address: {hostname}")
        if addr.is_link_local:
            raise ValueError(f"URL targets a link-local address: {hostname}")
        if addr.is_reserved:
            raise ValueError(f"URL targets a reserved IP address: {hostname}")
    except ValueError as exc:
        # Re-raise our own SSRF errors
        if "URL targets" in str(exc):
            raise
        # Not an IP address — it's a hostname, which is fine
        pass

    return url
