"""Application logging: console + optional daily rotating file (~30 days)."""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def setup_logging(
    *,
    level: str = "INFO",
    log_dir: str | None = "logs",
    log_file_name: str = "fasio.log",
    backup_count: int = 30,
) -> None:
    """Configure root + app loggers.

    When ``log_dir`` is set, writes ``fasio.log`` rotated at midnight and keeps
    ``backup_count`` days of history (default 30).
    """
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level.upper())

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    if log_dir:
        path = Path(log_dir)
        path.mkdir(parents=True, exist_ok=True)
        file_handler = TimedRotatingFileHandler(
            filename=str(path / log_file_name),
            when="midnight",
            interval=1,
            backupCount=backup_count,
            encoding="utf-8",
            utc=False,
        )
        file_handler.suffix = "%Y-%m-%d"
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)

    logging.getLogger("app").setLevel(level.upper())
