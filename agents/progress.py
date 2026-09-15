"""Progress bus so long-running nodes report while still executing."""
from __future__ import annotations
import queue, threading
from typing import Any

_local = threading.local()


def bind(q: "queue.Queue[dict[str, Any]] | None") -> None:
    _local.q = q


def emit(**event: Any) -> None:
    q = getattr(_local, "q", None)
    if q is not None:
        try: q.put_nowait(event)
        except Exception: pass
