from __future__ import annotations

import faulthandler
import logging
import os
import platform
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import importlib.metadata as metadata

LOG_PATH: Optional[Path] = None
_STDERR_FILE = None
_STDERR_REDIRECTED = False


def setup_logging() -> Path:
    global LOG_PATH, _STDERR_FILE, _STDERR_REDIRECTED

    logs_dir = Path(__file__).resolve().parent / "data" / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    LOG_PATH = logs_dir / "ozon_app.log"

    logger = logging.getLogger()
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )

        file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler(sys.__stdout__)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    if not _STDERR_REDIRECTED:
        try:
            _STDERR_FILE = open(LOG_PATH, "a", buffering=1, encoding="utf-8")
            if sys.stderr and hasattr(sys.stderr, "fileno"):
                os.dup2(_STDERR_FILE.fileno(), sys.stderr.fileno())
                _STDERR_REDIRECTED = True
                faulthandler.enable(file=_STDERR_FILE)
        except Exception:
            logging.getLogger(__name__).exception("Failed to redirect stderr to log file.")

    _install_exception_hooks()
    _log_environment()
    return LOG_PATH


def get_log_path() -> Optional[Path]:
    return LOG_PATH


def _install_exception_hooks() -> None:
    def excepthook(exc_type, exc, tb) -> None:
        logging.getLogger("uncaught").exception("Unhandled exception", exc_info=(exc_type, exc, tb))

    def thread_excepthook(args) -> None:
        logging.getLogger("thread").exception(
            "Unhandled thread exception",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = excepthook
    if hasattr(threading, "excepthook"):
        threading.excepthook = thread_excepthook  # type: ignore[assignment]


def _log_environment() -> None:
    logger = logging.getLogger("env")
    logger.info("Logging started at %s", datetime.now().isoformat(timespec="seconds"))
    logger.info("Python: %s", sys.version.replace("\n", " "))
    logger.info("Platform: %s", platform.platform())
    try:
        logger.info("Playwright: %s", metadata.version("playwright"))
    except Exception:
        logger.exception("Failed to read Playwright version")
    try:
        logger.info("Playwright-stealth: %s", metadata.version("playwright-stealth"))
    except Exception:
        logger.exception("Failed to read playwright-stealth version")
