"""
Progress bus.

A LangGraph node only returns its update when it *finishes*. The drafting node
makes one LLM call per section, so a 7-section RFP can run for minutes with no
visible output — the UI looks frozen.

This module lets any node push fine-grained progress while it is still running.
`stream_pipeline` runs the graph on a worker thread and drains this queue, so
the browser sees each section land as it completes.
"""
from __future__ import annotations
import queue
import threading
from typing import Any

_local = threading.local()


def bind(q: "queue.Queue[dict[str, Any]] | None") -> None:
    """Attach a queue to the current thread (None to detach)."""
    _local.q = q


def emit(**event: Any) -> None:
    """Push a progress event. A no-op when nothing is listening."""
    q = getattr(_local, "q", None)
    if q is not None:
        try:
            q.put_nowait(event)
        except Exception:
            pass
