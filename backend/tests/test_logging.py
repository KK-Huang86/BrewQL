import io
import logging
import re

from app.logging_setup import configure_logging


def test_app_logs_carry_timestamp_level_and_logger_name():
    stream = io.StringIO()
    configure_logging(stream=stream)

    logging.getLogger("app.llm").info("bedrock call model=m")

    line = stream.getvalue().strip()
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{4} INFO app\.llm bedrock call model=m", line), line


def test_debug_is_hidden_by_default():
    stream = io.StringIO()
    configure_logging(stream=stream)

    logging.getLogger("app.llm").debug("noise")

    assert stream.getvalue() == ""
