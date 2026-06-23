from __future__ import annotations

from maya.logging_setup import configure_logging


def test_configure_logging_creates_three_log_files(tmp_path):
    loggers = configure_logging(tmp_path)

    for name, logger in loggers.items():
        logger.info("hello from %s", name)

    for short_name in ("app", "llm", "api"):
        log_path = tmp_path / "logs" / short_name / f"{short_name}.log"
        assert log_path.exists()
        assert log_path.read_text().strip() != ""


def test_configure_logging_is_safe_to_call_twice(tmp_path):
    configure_logging(tmp_path)
    loggers = configure_logging(tmp_path)

    for logger in loggers.values():
        assert len(logger.handlers) == 2
