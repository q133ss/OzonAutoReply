from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/147.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class BrowserProfileConfig:
    locale: str = "ru-RU"
    timezone_id: str = "Europe/Moscow"
    color_scheme: str = "light"
    viewport_width: int = 1440
    viewport_height: int = 900

    @property
    def viewport(self) -> Dict[str, int]:
        return {"width": self.viewport_width, "height": self.viewport_height}

    @property
    def screen(self) -> Dict[str, int]:
        return {"width": self.viewport_width, "height": self.viewport_height}

    @property
    def launch_args(self) -> list[str]:
        return [
            "--start-maximized",
            "--disable-blink-features=AutomationControlled",
            "--accept-lang=ru-RU,ru",
            "--lang=ru-RU",
        ]


DEFAULT_BROWSER_PROFILE = BrowserProfileConfig()


def find_chrome_executable() -> Optional[str]:
    env_path = os.environ.get("OZON_CHROME_EXECUTABLE")
    candidates = [
        env_path,
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        str(Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def build_persistent_context_kwargs(
    proxy: Optional[Dict[str, str]] = None,
    config: BrowserProfileConfig = DEFAULT_BROWSER_PROFILE,
) -> Dict[str, Any]:
    chrome_executable = find_chrome_executable()
    kwargs: Dict[str, Any] = {
        "headless": False,
        "ignore_default_args": ["--enable-automation"],
        "args": config.launch_args,
        "locale": config.locale,
        "timezone_id": config.timezone_id,
        "color_scheme": config.color_scheme,
        "viewport": config.viewport,
        "screen": config.screen,
        "extra_http_headers": {"Accept-Language": "ru-RU,ru;q=0.9"},
    }
    if chrome_executable:
        kwargs["executable_path"] = chrome_executable
    if proxy:
        kwargs["proxy"] = proxy
    return kwargs


def build_init_script() -> str:
    return ""


def apply_browser_profile(context: Any, logger: Optional[logging.Logger] = None) -> None:
    from playwright_stealth import Stealth

    stealth = Stealth(navigator_languages_override=("ru-RU", "ru"))
    context_stealth_applied = False
    try:
        stealth.apply_stealth_sync(context)
        context_stealth_applied = True
        if logger:
            logger.info("Applied stealth to browser context")
    except Exception:
        if logger:
            logger.exception("Failed to apply stealth to browser context")

    def _configure_page(page: Any) -> None:
        if context_stealth_applied:
            return
        try:
            stealth.apply_stealth_sync(page)
            if logger:
                logger.info("Applied stealth to page: %s", page.url)
        except Exception:
            if logger:
                logger.exception("Failed to apply stealth to page")

    for page in list(context.pages):
        _configure_page(page)
    context.on("page", _configure_page)
