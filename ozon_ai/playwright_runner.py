from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import traceback
from pathlib import Path
from typing import Optional

from .browser_profile import apply_browser_profile, build_persistent_context_kwargs
from .logging_utils import setup_logging
from .proxy import ProxyConfig


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
    parser.add_argument("--proxy-config")
    parser.add_argument("--profile-dir", required=True)
    parser.add_argument("--mode", default="new_account")
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger("playwright.runner")

    control_path = Path(args.control_path)
    status_path = Path(args.status_path)
    profile_dir = Path(args.profile_dir).resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)

    playwright = None
    context = None
    page = None
    proxy_config = None
    if args.proxy_config:
        try:
            proxy_config = ProxyConfig.from_dict(json.loads(Path(args.proxy_config).read_text(encoding="utf-8")))
            proxy_config.validate()
        except Exception:
            logger.exception("Failed to read proxy config")
            _write_status(status_path, "error")
            status_path.with_suffix(".error").write_text(traceback.format_exc(), encoding="utf-8")
            return 1

    try:
        from playwright.sync_api import sync_playwright

        logger.info(
            "Runner starting. url=%s mode=%s profile_dir=%s proxy=%s",
            args.url,
            args.mode,
            profile_dir,
            bool(proxy_config and proxy_config.enabled),
        )
        playwright = sync_playwright().start()
        proxy = proxy_config.to_playwright_proxy() if proxy_config else None
        context = playwright.chromium.launch_persistent_context(
            str(profile_dir),
            **build_persistent_context_kwargs(proxy=proxy),
        )
        apply_browser_profile(context, logger)
        page = context.pages[0] if context.pages else context.new_page()
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
                    logger.info("Storage state saved. profile_dir=%s", profile_dir)
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
            if playwright:
                time.sleep(0.2)
                playwright.stop()
        except Exception:
            logger.exception("Failed to stop Playwright")

    return 0


if __name__ == "__main__":
    sys.exit(main())
