"""HTML sanitization and HTML→plain-text conversion for episode descriptions.

Two public functions:
- sanitize_html(text)  → safe HTML subset (stored in DB, rendered in UI)
- html_to_text(text)   → structured plain text (sent to YouTube API)
"""
from __future__ import annotations

import re
from html.parser import HTMLParser

import nh3

# Tags allowed in stored/displayed descriptions
_ALLOWED_TAGS = {
    "p", "br",
    "strong", "b", "em", "i", "u",
    "a",
    "ul", "ol", "li",
    "blockquote",
    "h1", "h2", "h3", "h4", "h5", "h6",
}

# Only <a href="…"> is allowed; href must be http/https/mailto
_ALLOWED_ATTRS: dict[str, set[str]] = {"a": {"href"}}
_ALLOWED_SCHEMES = {"http", "https", "mailto"}

_BLOCK_OPEN = {"p", "div", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6"}
_BLOCK_CLOSE = _BLOCK_OPEN
_LIST_TAGS = {"ul", "ol"}


def sanitize_html(text: str) -> str:
    """Strip dangerous HTML, keeping a safe structural subset.

    Safe to render with Jinja2's ``| safe`` filter after this call.
    Idempotent — calling twice produces the same result.
    """
    if not text or not text.strip():
        return ""
    return nh3.clean(
        text,
        tags=_ALLOWED_TAGS,
        attributes=_ALLOWED_ATTRS,
        url_schemes=_ALLOWED_SCHEMES,
        link_rel=None,  # we handle rel in the template
    )


# ── HTML → structured plain text ─────────────────────────────────────────────

class _TextConverter(HTMLParser):
    """Walk sanitized HTML and produce readable plain text for YouTube."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._pending_href: str | None = None
        self._link_text: list[str] = []
        self._in_link = False

    # helpers -----------------------------------------------------------------

    def _ensure_newlines(self, n: int) -> None:
        """Make sure the output ends with at least *n* consecutive newlines."""
        tail = "".join(self._parts)
        current = len(tail) - len(tail.rstrip("\n"))
        needed = n - current
        if needed > 0:
            self._parts.append("\n" * needed)

    def _append(self, text: str) -> None:
        if self._in_link:
            self._link_text.append(text)
        else:
            self._parts.append(text)

    # HTMLParser callbacks ----------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _BLOCK_OPEN:
            self._ensure_newlines(2)
        elif tag == "br":
            self._parts.append("\n")
        elif tag in _LIST_TAGS:
            self._ensure_newlines(1)
        elif tag == "li":
            self._ensure_newlines(1)
            self._parts.append("• ")
        elif tag == "a":
            attrs_dict = dict(attrs)
            href = (attrs_dict.get("href") or "").strip()
            if href and any(href.startswith(s + ":") for s in _ALLOWED_SCHEMES):
                self._pending_href = href
                self._in_link = True
                self._link_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag in _BLOCK_CLOSE:
            self._ensure_newlines(2)
        elif tag in _LIST_TAGS:
            self._ensure_newlines(1)
        elif tag == "a" and self._in_link:
            link_text = "".join(self._link_text).strip()
            href = self._pending_href or ""
            # Normalize display href: strip "mailto:" prefix
            display = href[len("mailto:"):] if href.startswith("mailto:") else href
            if link_text and link_text not in (href, display):
                self._parts.append(f"{link_text} ({display})")
            else:
                self._parts.append(display)
            self._in_link = False
            self._pending_href = None
            self._link_text = []

    def handle_data(self, data: str) -> None:
        self._append(data)

    # result ------------------------------------------------------------------

    def result(self) -> str:
        text = "".join(self._parts)
        text = re.sub(r"[ \t]+", " ", text)          # collapse horizontal whitespace
        text = re.sub(r" \n", "\n", text)             # trailing spaces before newlines
        text = re.sub(r"\n[ \t]+", "\n", text)        # leading spaces after newlines
        text = re.sub(r"\n{3,}", "\n\n", text)        # max two consecutive newlines
        return text.strip()


def html_to_text(text: str) -> str:
    """Convert (sanitized) HTML description to structured plain text.

    Preserves paragraph breaks, list items (as bullets), and links as
    ``visible text (url)`` — appropriate for YouTube video descriptions.
    """
    if not text or not text.strip():
        return ""
    # Sanitize first so the converter only ever sees safe markup
    clean = sanitize_html(text)
    converter = _TextConverter()
    converter.feed(clean)
    return converter.result()
