"""
Progress bus so long-running nodes report while still executing.

The queue is stored in thread-local storage. Drafting now runs sections on a
worker pool, so `current()` lets the pool re-bind the same queue inside each
worker — otherwise progress from those threads would be silently dropped.
"""
from __future__ import annotations
import queue
import threading
from typing import Any

_local = threading.local()


def bind(q: "queue.Queue[dict[str, Any]] | None") -> None:
    _local.q = q


def current() -> "queue.Queue[dict[str, Any]] | None":
    """The queue bound to this thread, if any."""
    return getattr(_local, "q", None)


def emit(**event: Any) -> None:
    """Push a progress event. A no-op when nothing is listening."""
    q = current()
    if q is not None:
        try:
            q.put_nowait(event)
        except Exception:
            pass
