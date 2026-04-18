from __future__ import annotations

import sys
from pathlib import Path


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def package_root() -> Path:
    return app_root() / "ozon_ai"


def db_path() -> Path:
    return app_root() / "ozon_ai.db"


def data_dir() -> Path:
    path = package_root() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def sessions_dir() -> Path:
    path = data_dir() / "sessions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def browser_profiles_dir() -> Path:
    path = data_dir() / "browser_profiles"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def env_path() -> Path:
    return app_root() / ".env"
