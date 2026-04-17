from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from .browser_profile import apply_browser_profile, build_persistent_context_kwargs
from .proxy import ProxyConfig


class PlaywrightAccountWorker(QObject):
    started = pyqtSignal()
    error = pyqtSignal(str)
    session_saved = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(
        self,
        url: str,
        proxy_config: Optional[ProxyConfig] = None,
        profile_dir: Optional[str] = None,
    ) -> None:
        super().__init__()
        self._url = url
        self._proxy_config = proxy_config
        self._profile_dir = Path(profile_dir).resolve() if profile_dir else Path(tempfile.mkdtemp(prefix="ozon_profile_"))
        self._owns_profile_dir = profile_dir is None
        self._playwright = None
        self._context = None
        self._page = None
        self._stopped = False
        self._logger = logging.getLogger("playwright.worker")

    @pyqtSlot()
    def start(self) -> None:
        if self._stopped:
            return
        try:
            from playwright.sync_api import sync_playwright

            self._logger.info("Launching Playwright browser. url=%s profile=%s", self._url, self._profile_dir)
            self._playwright = sync_playwright().start()
            proxy = self._proxy_config.to_playwright_proxy() if self._proxy_config else None
            self._profile_dir.mkdir(parents=True, exist_ok=True)
            self._context = self._playwright.chromium.launch_persistent_context(
                str(self._profile_dir),
                **build_persistent_context_kwargs(proxy=proxy),
            )
            apply_browser_profile(self._context, self._logger)
            self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
            self._page.goto(self._url, wait_until="domcontentloaded")
            self.started.emit()
        except Exception as exc:
            self._logger.exception("Playwright start failed")
            self.error.emit(str(exc))
            self.stop()

    @pyqtSlot(str)
    def save_session(self, path: str) -> None:
        if self._stopped:
            return
        try:
            if not self._context:
                raise RuntimeError("Браузер еще не запущен.")
            self._logger.info("Saving storage state to %s", path)
            self._context.storage_state(path=path)
            self._logger.info("Storage state saved")
            self.session_saved.emit(path)
        except Exception as exc:
            self._logger.exception("Storage state save failed")
            self.error.emit(str(exc))

    @pyqtSlot()
    def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        try:
            if self._context:
                self._logger.info("Closing browser context")
                self._context.close()
        except Exception:
            self._logger.exception("Failed to close browser context")
            pass
        try:
            if self._playwright:
                self._logger.info("Stopping Playwright")
                time.sleep(0.2)
                self._playwright.stop()
        except Exception:
            self._logger.exception("Failed to stop Playwright")
            pass
        if self._owns_profile_dir:
            try:
                import shutil

                shutil.rmtree(self._profile_dir, ignore_errors=True)
            except Exception:
                self._logger.exception("Failed to remove temporary profile dir")
        self._context = None
        self._playwright = None
        self.finished.emit()
