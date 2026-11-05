"""Log format for the app's own loggers: ISO timestamp, level, logger name, message."""

import logging
import sys
from typing import TextIO

FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def configure_logging(level: int = logging.INFO, stream: TextIO | None = None) -> None:
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.setFormatter(logging.Formatter(FORMAT, DATE_FORMAT))
    # Only the "app" tree: uvicorn keeps its own access/error log format.
    logger = logging.getLogger("app")
    logger.handlers[:] = [handler]
    logger.setLevel(level)
    logger.propagate = False
