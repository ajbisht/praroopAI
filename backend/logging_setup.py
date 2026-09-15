"""
Central logging for PraroopAI.

Level is controlled by LOG_LEVEL in .env:

    TRACE   - everything, including full prompts and full model replies
    DEBUG   - each LLM call with timing, sizes and a response preview
    INFO    - pipeline milestones (default)
    WARNING - only problems
    ERROR   - only failures

TRACE is a custom level (5) below DEBUG, for full prompt/response dumps.
"""
from __future__ import annotations
import logging
import os
import sys

TRACE_LEVEL = 5
logging.addLevelName(TRACE_LEVEL, "TRACE")


def _trace(self, msg, *args, **kwargs):
    if self.isEnabledFor(TRACE_LEVEL):
        self._log(TRACE_LEVEL, msg, args, **kwargs)


logging.Logger.trace = _trace  # type: ignore[attr-defined]

_COLORS = {
    "TRACE": "\033[90m", "DEBUG": "\033[36m", "INFO": "\033[32m",
    "WARNING": "\033[33m", "ERROR": "\033[31m", "CRITICAL": "\033[41m",
}
_RESET = "\033[0m"


class _Formatter(logging.Formatter):
    def __init__(self, color: bool):
        super().__init__("%(asctime)s %(levelname)-7s %(name)-22s %(message)s",
                         datefmt="%H:%M:%S")
        self.color = color

    def format(self, record):
        out = super().format(record)
        if self.color:
            c = _COLORS.get(record.levelname, "")
            if c:
                out = f"{c}{out}{_RESET}"
        return out


_configured = False


def setup_logging(level: str | None = None) -> str:
    """Configure root logging once. Returns the effective level name."""
    global _configured
    lvl_name = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    lvl = TRACE_LEVEL if lvl_name == "TRACE" else \
        getattr(logging, lvl_name, logging.INFO)

    root = logging.getLogger("praroopai")
    root.setLevel(lvl)

    if not _configured:
        h = logging.StreamHandler(sys.stdout)
        # colour only when attached to a real terminal
        h.setFormatter(_Formatter(color=sys.stdout.isatty()))
        root.addHandler(h)
        root.propagate = False
        _configured = True
    else:
        for h in root.handlers:
            h.setLevel(lvl)

    # keep third-party noise down unless we're debugging hard
    if lvl > TRACE_LEVEL:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
    return lvl_name


def get_logger(name: str) -> logging.Logger:
    """Child logger, e.g. get_logger('llm') -> 'praroopai.llm'."""
    return logging.getLogger(f"praroopai.{name}")
