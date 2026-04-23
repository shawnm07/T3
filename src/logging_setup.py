"""Consistent logging to both stdout and rotating files per-script."""
from __future__ import annotations
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)


def setup_logging(name: str, level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger()
    logger.setLevel(level)
    if logger.handlers:
        return logging.getLogger(name)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    fh = RotatingFileHandler(LOG_DIR / f"{name}.log", maxBytes=5_000_000, backupCount=3)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logging.getLogger(name)
