"""In-memory progress store for long-running background operations.

Keys: "download:{episode_id}", "render:{episode_id}", "upload:{episode_id}"
Values: 0-100 (percentage).  Missing key = no active operation.

Thread-safe enough for a single-worker uvicorn: dict reads/writes of integers
are atomic under the GIL, and a slightly stale percentage in the UI is fine.
"""
from __future__ import annotations

_store: dict[str, int] = {}


def set_progress(kind: str, episode_id: int, pct: int) -> None:
    _store[f"{kind}:{episode_id}"] = max(0, min(100, pct))


def get_progress(kind: str, episode_id: int) -> int:
    return _store.get(f"{kind}:{episode_id}", 0)


def clear_progress(kind: str, episode_id: int) -> None:
    _store.pop(f"{kind}:{episode_id}", None)
