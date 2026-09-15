"""Central logging. LOG_LEVEL=TRACE|DEBUG|INFO|WARNING|ERROR in .env."""
from __future__ import annotations
import logging, os, sys

TRACE_LEVEL = 5
logging.addLevelName(TRACE_LEVEL, "TRACE")


def _trace(self, msg, *a, **kw):
    if self.isEnabledFor(TRACE_LEVEL):
        self._log(TRACE_LEVEL, msg, a, **kw)


logging.Logger.trace = _trace

_C = {"TRACE":"\033[90m","DEBUG":"\033[36m","INFO":"\033[32m",
      "WARNING":"\033[33m","ERROR":"\033[31m","CRITICAL":"\033[41m"}


class _F(logging.Formatter):
    def __init__(self, color):
        super().__init__("%(asctime)s %(levelname)-7s %(name)-22s %(message)s", datefmt="%H:%M:%S")
        self.color = color
    def format(self, r):
        out = super().format(r)
        return f"{_C.get(r.levelname,'')}{out}\033[0m" if self.color and r.levelname in _C else out


_done = False


def setup_logging(level: str | None = None) -> str:
    global _done
    name = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    lvl = TRACE_LEVEL if name == "TRACE" else getattr(logging, name, logging.INFO)
    root = logging.getLogger("praroopai"); root.setLevel(lvl)
    if not _done:
        h = logging.StreamHandler(sys.stdout); h.setFormatter(_F(sys.stdout.isatty()))
        root.addHandler(h); root.propagate = False; _done = True
    for h in root.handlers: h.setLevel(lvl)
    if lvl > TRACE_LEVEL:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
    return name


def get_logger(n: str) -> logging.Logger:
    return logging.getLogger(f"praroopai.{n}")
