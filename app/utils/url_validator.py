"""SSRF protection: validate URLs before making outbound HTTP requests."""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


def _check_addr(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if addr.is_loopback:
        raise ValueError(f"URL targets a loopback address: {addr}")
    if addr.is_private:
        raise ValueError(f"URL targets a private IP address: {addr}")
    if addr.is_link_local:
        raise ValueError(f"URL targets a link-local address: {addr}")
    if addr.is_reserved:
        raise ValueError(f"URL targets a reserved IP address: {addr}")


def validate_external_url(url: str) -> str:
    """Validate that a URL is safe to fetch externally (SSRF protection).

    Raises ValueError if:
    - The scheme is not http or https
    - The host resolves to a private, loopback, link-local, or reserved IP
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

    try:
        # Literal IP address — check directly
        _check_addr(ipaddress.ip_address(hostname))
    except ValueError as exc:
        if "URL targets" in str(exc):
            raise
        # Not a literal IP — resolve the hostname and check every returned address
        try:
            results = socket.getaddrinfo(hostname, None)
            for result in results:
                _check_addr(ipaddress.ip_address(result[4][0]))
        except (socket.gaierror, UnicodeError):
            raise ValueError(f"Cannot resolve hostname: {hostname}")

    return url
