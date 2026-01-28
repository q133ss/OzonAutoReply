from __future__ import annotations

import logging
import time

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


class PlaywrightAccountWorker(QObject):
    started = pyqtSignal()
    error = pyqtSignal(str)
    session_saved = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, url: str) -> None:
        super().__init__()
        self._url = url
        self._playwright = None
        self._browser = None
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
            from playwright_stealth import Stealth

            self._logger.info("Launching Playwright browser. url=%s", self._url)
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=False)
            self._context = self._browser.new_context()
            self._page = self._context.new_page()
            Stealth().apply_stealth_sync(self._page)
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
            if self._browser:
                self._logger.info("Closing browser")
                self._browser.close()
        except Exception:
            self._logger.exception("Failed to close browser")
            pass
        try:
            if self._playwright:
                self._logger.info("Stopping Playwright")
                time.sleep(0.2)
                self._playwright.stop()
        except Exception:
            self._logger.exception("Failed to stop Playwright")
            pass
        self._context = None
        self._browser = None
        self._playwright = None
        self.finished.emit()
