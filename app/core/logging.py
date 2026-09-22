from __future__ import annotations
import logging
import logging.config
import os
from pathlib import Path


def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "INFO").upper()
    log_dir = Path(os.getenv("LOG_DIR", "./storage/logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {"format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s"},
        },
        "handlers": {
            "console": {"class": "logging.StreamHandler", "formatter": "standard", "stream": "ext://sys.stdout"},
            "file": {"class": "logging.handlers.RotatingFileHandler", "formatter": "standard", "filename": str(log_dir / "app.log"), "maxBytes": 10_000_000, "backupCount": 5, "encoding": "utf-8"},
        },
        "root": {"level": level, "handlers": ["console", "file"]},
    })


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
