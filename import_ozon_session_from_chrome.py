from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from ozon_ai.db import Database
from ozon_ai.ozon_reviews import (
    _clear_session_needs_relogin,
    _extract_company_id,
    _load_storage_state,
    _session_needs_relogin,
)


DEFAULT_CDP_URL = "http://127.0.0.1:9222"


def _default_sessions_dir() -> Path:
    return Path(__file__).resolve().parent / "ozon_ai" / "data" / "sessions"


def _default_profile_dir() -> Path:
    return Path(__file__).resolve().parent / "ozon_ai" / "data" / "real_chrome_profile"


def _find_seller_page(contexts: list[object]):
    for context in contexts:
        for page in context.pages:
            if "seller.ozon.ru" in page.url:
                return page
    for context in contexts:
        if context.pages:
            return context.pages[0]
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import Ozon cookies/localStorage from a real Chrome session opened with remote debugging."
    )
    parser.add_argument("--cdp-url", default=DEFAULT_CDP_URL)
    parser.add_argument("--account-id", type=int)
    parser.add_argument("--name", default="")
    parser.add_argument("--db", default=str(Path(__file__).resolve().parent / "ozon_ai.db"))
    args = parser.parse_args()

    sessions_dir = _default_sessions_dir()
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_path = sessions_dir / f"ozon_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex}.json"

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(args.cdp_url)
        contexts = list(browser.contexts)
        if not contexts:
            raise RuntimeError("No Chrome contexts found. Is Chrome open with remote debugging enabled?")
        page = _find_seller_page(contexts)
        if page is None:
            raise RuntimeError("No Chrome page found.")
        if "seller.ozon.ru" not in page.url:
            print(f"Warning: active page is not seller.ozon.ru: {page.url}")
        contexts[0].storage_state(path=str(session_path))

    storage_state = _load_storage_state(session_path)
    if not storage_state:
        print(f"Session file was written, but could not be read: {session_path}")
        return 2

    company_id = _extract_company_id(storage_state)
    needs_relogin = _session_needs_relogin(session_path, storage_state)
    _clear_session_needs_relogin(session_path)

    db = Database(args.db)
    try:
        db.ensure_schema()
        created_at = datetime.now().isoformat(timespec="seconds")
        profile_dir = str(_default_profile_dir())
        if args.account_id:
            account = db.get_account(args.account_id)
            if not account:
                raise RuntimeError(f"Account id {args.account_id} was not found in DB.")
            db.update_account_session(
                args.account_id,
                str(session_path),
                profile_dir,
                created_at,
            )
            print(f"Updated account id: {args.account_id}")
        else:
            name = args.name.strip() or f"Ozon {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            db.add_account(name, str(session_path), profile_dir, created_at)
            print(f"Added account: {name}")
    finally:
        db.close()

    print(f"Session: {session_path}")
    print(f"Company id: {company_id or '<missing>'}")
    print(f"Needs relogin: {needs_relogin}")
    if needs_relogin or not company_id:
        print("Result: imported, but the session does not look fully active. Open Ozon reviews in Chrome and import again.")
        return 3
    print("Result: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
