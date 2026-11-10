"""Log format for the app's own loggers: one JSON object per line, so Alloy can parse it (observe-with-grafana D6)."""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import TextIO

RESERVED = ("time", "level", "logger", "message")
# Attributes every LogRecord has; anything else on a record came from extra={...}.
_RECORD_ATTRS = frozenset(vars(logging.LogRecord("", 0, "", 0, "", None, None))) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        line = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in vars(record).items():
            # Structured fields sit at the top level; they never replace the four keys above.
            if key not in _RECORD_ATTRS and key not in RESERVED:
                line[key] = value
        if record.exc_info:
            line["exc_info"] = self.formatException(record.exc_info)
        # default=str: a value JSON cannot encode is logged as text instead of losing the line.
        return json.dumps(line, ensure_ascii=False, default=str)


def configure_logging(level: int = logging.INFO, stream: TextIO | None = None) -> None:
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(JsonFormatter())
    # Only the "app" tree: uvicorn's error log keeps its own format, and its access log is off.
    logger = logging.getLogger("app")
    logger.handlers[:] = [handler]
    logger.setLevel(level)
    logger.propagate = False
