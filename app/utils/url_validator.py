"""SSRF protection: validate URLs before making outbound HTTP requests."""
from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlparse

_CGNAT = ipaddress.ip_network("100.64.0.0/10")

# Matches strings that look like IPv4 literals (digits and dots only).
# Used to catch octal notation (e.g. "0177.0.0.1") before DNS resolution.
_IP_LIKE = re.compile(r"^[\d.]+$")


def _check_addr(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    # Unwrap IPv4-mapped IPv6 (::ffff:x.x.x.x) so private-range checks apply
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped:
        addr = addr.ipv4_mapped

    if addr.is_loopback:
        raise ValueError(f"URL targets a loopback address: {addr}")
    if addr.is_private:
        raise ValueError(f"URL targets a private IP address: {addr}")
    if addr.is_link_local:
        raise ValueError(f"URL targets a link-local address: {addr}")
    if addr.is_reserved:
        raise ValueError(f"URL targets a reserved IP address: {addr}")
    if isinstance(addr, ipaddress.IPv4Address) and addr in _CGNAT:
        raise ValueError(f"URL targets a CG-NAT address: {addr}")


def validate_external_url(url: str) -> str:
    """Validate that a URL is safe to fetch externally (SSRF protection).

    Raises ValueError if:
    - The scheme is not http or https
    - The host resolves to a private, loopback, link-local, reserved, or CG-NAT IP
    - The hostname looks like an octal/decimal IP literal that getaddrinfo would interpret
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

    # Reject octal-looking IP literals before they reach the OS resolver.
    # ipaddress.ip_address() rejects octal notation (raises ValueError), but
    # some OS resolvers (Linux) interpret "0177.0.0.1" as 127.0.0.1.
    if _IP_LIKE.match(hostname):
        try:
            _check_addr(ipaddress.ip_address(hostname))
        except ValueError as exc:
            # If it parsed as an IP and we blocked it, re-raise.
            # If ipaddress itself rejected it (octal/malformed), also block.
            raise ValueError(f"Invalid or disallowed IP literal: {hostname}") from exc
        return url

    try:
        # Literal IP address (IPv6 or standard IPv4) — check directly
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
