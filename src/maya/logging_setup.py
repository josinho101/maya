"""Three-stream logging setup (plan.md §8): app/llm/api loggers, each with a file handler under
`<root_dir>/logs/{app,llm,api}/` plus a shared console handler. Full rotating-handler upgrade is
deferred to F14 — this is deliberately the minimal version."""

from __future__ import annotations

import logging
from pathlib import Path

_LOGGER_NAMES = ("maya.app", "maya.llm", "maya.api")
_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def configure_logging(root_dir: Path, level: int = logging.INFO) -> dict[str, logging.Logger]:
    root_dir = Path(root_dir)
    formatter = logging.Formatter(_LOG_FORMAT)

    loggers: dict[str, logging.Logger] = {}
    for name in _LOGGER_NAMES:
        short_name = name.removeprefix("maya.")
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.handlers.clear()

        log_path = root_dir / "logs" / short_name / f"{short_name}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        loggers[name] = logger

    return loggers
