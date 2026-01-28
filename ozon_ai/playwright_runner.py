from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import traceback
from pathlib import Path
from typing import Optional

from .logging_utils import setup_logging


def _write_status(path: Path, status: str, payload: Optional[str] = None) -> None:
    if payload:
        data = f"{status}|{payload}"
    else:
        data = status
    path.write_text(data, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--control-path", required=True)
    parser.add_argument("--status-path", required=True)
    parser.add_argument("--log-path")
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger("playwright.runner")

    control_path = Path(args.control_path)
    status_path = Path(args.status_path)

    playwright = None
    browser = None
    context = None
    page = None

    try:
        from playwright.sync_api import sync_playwright
        from playwright_stealth import Stealth

        logger.info("Runner starting. url=%s", args.url)
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        Stealth().apply_stealth_sync(page)
        page.goto(args.url, wait_until="domcontentloaded")
        _write_status(status_path, "ready")

        while True:
            if control_path.exists():
                try:
                    payload = json.loads(control_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    payload = {}
                control_path.unlink(missing_ok=True)
                action = payload.get("action")
                if action == "save":
                    session_path = payload.get("session_path")
                    if not session_path:
                        raise RuntimeError("Missing session_path in save command.")
                    logger.info("Saving storage state to %s", session_path)
                    context.storage_state(path=session_path)
                    logger.info("Storage state saved")
                    _write_status(status_path, "saved", session_path)
                    break
                if action == "stop":
                    _write_status(status_path, "stopped")
                    break
            if page and page.is_closed():
                _write_status(status_path, "closed")
                break
            time.sleep(0.2)
    except Exception:
        logger.exception("Runner failed")
        _write_status(status_path, "error")
        status_path.with_suffix(".error").write_text(traceback.format_exc(), encoding="utf-8")
        return 1
    finally:
        try:
            if context:
                context.close()
        except Exception:
            logger.exception("Failed to close context")
        try:
            if browser:
                browser.close()
        except Exception:
            logger.exception("Failed to close browser")
        try:
            if playwright:
                time.sleep(0.2)
                playwright.stop()
        except Exception:
            logger.exception("Failed to stop Playwright")

    return 0


if __name__ == "__main__":
    sys.exit(main())
