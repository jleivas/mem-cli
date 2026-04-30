from __future__ import annotations

import logging
from pathlib import Path

from ..config import get_log_path


def configure_logging(level: int = logging.INFO, log_path: Path | None = None) -> None:
    destination = log_path or get_log_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(destination, encoding="utf-8"),
        ],
        force=True,
    )
