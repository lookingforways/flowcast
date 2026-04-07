"""In-memory progress store for long-running background operations.

Keys: "download:{episode_id}", "render:{episode_id}", "upload:{episode_id}"
Values: 0-100 (percentage).

_active tracks which operations are genuinely running so that 0% is not
confused with "no operation" by the polling endpoint.
"""
from __future__ import annotations

_store:  dict[str, int] = {}
_active: set[str]       = set()


def set_progress(kind: str, episode_id: int, pct: int) -> None:
    key = f"{kind}:{episode_id}"
    _store[key] = max(0, min(100, pct))
    _active.add(key)


def get_progress(kind: str, episode_id: int) -> int:
    return _store.get(f"{kind}:{episode_id}", 0)


def is_active(kind: str, episode_id: int) -> bool:
    return f"{kind}:{episode_id}" in _active


def clear_progress(kind: str, episode_id: int) -> None:
    key = f"{kind}:{episode_id}"
    _store.pop(key, None)
    _active.discard(key)
