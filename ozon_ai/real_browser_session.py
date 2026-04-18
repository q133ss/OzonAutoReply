from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from .app_paths import app_root, browser_profiles_dir, db_path as app_db_path, sessions_dir as app_sessions_dir
from .browser_profile import find_chrome_executable
from .db import Database
from .ozon_reviews import (
    _clear_session_needs_relogin,
    _extract_company_id,
    _load_storage_state,
    _session_needs_relogin,
)

OZON_LOGIN_URL = (
    "https://seller.ozon.ru/app/registration/signin?"
    "redirect=L3Jldmlld3M%2FX19ycj0xJmFidF9hdHQ9MQ%3D%3D"
)
OZON_REVIEWS_URL = "https://seller.ozon.ru/app/reviews"
DEFAULT_CDP_URL = "http://127.0.0.1:9222"
DEFAULT_CDP_PORT = 9222


@dataclass(frozen=True)
class ImportResult:
    session_path: Path
    profile_dir: Path
    created_at: str
    company_id: Optional[str]
    needs_relogin: bool
    account_id: Optional[int]
    account_name: Optional[str]


def project_base_dir() -> Path:
    return app_root()


def db_path() -> Path:
    return app_db_path()


def sessions_dir() -> Path:
    return app_sessions_dir()


def real_browser_profile_dir() -> Path:
    path = browser_profiles_dir() / "real_browser"
    path.mkdir(parents=True, exist_ok=True)
    return path


def open_real_browser(
    *,
    port: int = DEFAULT_CDP_PORT,
    start_url: str = OZON_LOGIN_URL,
) -> tuple[str, Path]:
    browser_path = find_chrome_executable()
    if not browser_path:
        raise RuntimeError("Google Chrome / Microsoft Edge not found.")

    profile_dir = real_browser_profile_dir()
    args = [
        browser_path,
        f"--remote-debugging-port={int(port)}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--lang=ru-RU",
        start_url,
    ]
    subprocess.Popen(args, cwd=str(project_base_dir()))
    return browser_path, profile_dir


def format_accounts() -> str:
    db = Database(str(db_path()))
    try:
        db.ensure_schema()
        accounts = db.list_accounts()
    finally:
        db.close()

    if not accounts:
        return "Аккаунтов в базе пока нет."

    lines = []
    for account in accounts:
        lines.append(f'{account["id"]}: {account["name"]}')
    return "\n".join(lines)


def _find_seller_page(contexts: list[object]):
    for context in contexts:
        for page in context.pages:
            if "seller.ozon.ru" in page.url:
                return page, context
    for context in contexts:
        if context.pages:
            return context.pages[0], context
    return None, None


def import_session_from_browser(
    *,
    cdp_url: str = DEFAULT_CDP_URL,
    account_id: Optional[int] = None,
    account_name: str = "",
) -> ImportResult:
    session_file = sessions_dir() / f"ozon_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex}.json"
    created_at = datetime.now().isoformat(timespec="seconds")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.connect_over_cdp(cdp_url)
        contexts = list(browser.contexts)
        if not contexts:
            raise RuntimeError("Не найден браузер с CDP. Сначала откройте реальный Chrome/Edge с remote debugging.")
        page, context = _find_seller_page(contexts)
        if context is None:
            raise RuntimeError("Не найдено ни одной вкладки браузера.")
        if page is not None and "seller.ozon.ru" not in page.url:
            raise RuntimeError("Откройте seller.ozon.ru в этом браузере и повторите импорт.")
        context.storage_state(path=str(session_file))

    storage_state = _load_storage_state(session_file)
    if not storage_state:
        raise RuntimeError(f"Не удалось прочитать сохраненную сессию: {session_file}")

    company_id = _extract_company_id(storage_state)
    needs_relogin = _session_needs_relogin(session_file, storage_state)
    _clear_session_needs_relogin(session_file)

    selected_account_id: Optional[int] = None
    selected_account_name: Optional[str] = None
    db = Database(str(db_path()))
    try:
        db.ensure_schema()
        profile_dir = str(real_browser_profile_dir())
        if account_id is not None:
            account = db.get_account(account_id)
            if not account:
                raise RuntimeError(f"Аккаунт id={account_id} не найден в базе.")
            db.update_account_session(account_id, str(session_file), profile_dir, created_at)
            selected_account_id = account_id
            selected_account_name = account["name"]
        else:
            selected_account_name = account_name.strip() or f"Ozon {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            db.add_account(selected_account_name, str(session_file), profile_dir, created_at)
            accounts = db.list_accounts()
            if accounts:
                selected_account_id = int(accounts[-1]["id"])
    finally:
        db.close()

    return ImportResult(
        session_path=session_file,
        profile_dir=real_browser_profile_dir(),
        created_at=created_at,
        company_id=company_id,
        needs_relogin=needs_relogin,
        account_id=selected_account_id,
        account_name=selected_account_name,
    )
