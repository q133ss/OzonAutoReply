"""Автоматическое продление сессии Ozon.

Токен продавца живёт около часа. Когда он протухает, API отвечает 401, и раньше
программа просто ждала человека: 1 августа она так простояла трое суток, выдав
180 ошибок в час и не отправив ни одного ответа.

Ждать не нужно. Вход восстанавливается без пароля и СМС — на форме входа
достаточно нажать «Войти», дальше срабатывает cookie SSO
(`__Secure-idp-token` на `.sso.ozon.ru`, живёт около года). Здесь мы делаем это
сами: открываем в уже запущенном Chrome страницу отзывов, при редиректе на форму
входа жмём кнопку и переносим свежие cookie в файлы сессий.

Компанию в браузере переключать не нужно. Вход у обоих магазинов общий, а магазин
выбирают cookie `sc_company_id` и `bacntid` — свежие cookie раскладываются по
всем аккаунтам, а «магазинные» берутся из прежнего файла сессии. Проверено:
после такой раскладки оба магазина отдают свои отзывы, списки не пересекаются.
"""

from __future__ import annotations

import copy
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .db import Database
from .ozon_reviews import (
    _clear_session_needs_relogin,
    _mark_session_needs_relogin,
    _session_needs_relogin,
    save_session_user_agent,
)
from .real_browser_session import DEFAULT_CDP_PORT

logger = logging.getLogger(__name__)

REVIEWS_URL = "https://seller.ozon.ru/app/reviews"
SIGNIN_MARKER = "/app/registration/signin"
# Эти cookie определяют магазин и у каждого аккаунта свои - их не трогаем.
COMPANY_COOKIES = ("sc_company_id", "bacntid")
DEFAULT_REFRESH_MINUTES = 15


class KeepaliveError(RuntimeError):
    """Сессию продлить не удалось."""


def _cdp_url(port: int = DEFAULT_CDP_PORT) -> str:
    return f"http://127.0.0.1:{port}"


def _seller_page(context):
    for page in context.pages:
        if "seller.ozon.ru" in page.url:
            return page
    return context.new_page()


def _click_signin_button(page) -> bool:
    """Жмёт «Войти» на форме входа.

    Кнопка ведёт в SSO, где уже лежит cookie сессии, поэтому ни телефон, ни код
    вводить не приходится.
    """
    candidates = (
        lambda: page.get_by_role("button", name="Войти", exact=True),
        lambda: page.get_by_role("link", name="Войти", exact=True),
        lambda: page.locator("button:text-is('Войти')"),
        lambda: page.locator("a:text-is('Войти')"),
    )
    for build in candidates:
        try:
            locator = build().first
            locator.wait_for(state="visible", timeout=5_000)
            locator.click(timeout=10_000)
            return True
        except Exception:
            continue
    return False


def _open_reviews_page(page, timeout_ms: int = 60_000) -> None:
    page.goto(REVIEWS_URL, wait_until="domcontentloaded", timeout=timeout_ms)
    # Кабинет - SPA: редирект на форму входа приходит уже после загрузки.
    page.wait_for_timeout(4_000)
    if SIGNIN_MARKER not in page.url:
        return

    logger.info("Сессия Ozon протухла, нажимаю «Войти» на форме входа")
    if not _click_signin_button(page):
        raise KeepaliveError("На форме входа не нашлась кнопка «Войти»")
    try:
        page.wait_for_url(
            lambda url: SIGNIN_MARKER not in url,
            timeout=timeout_ms,
        )
    except Exception as exc:
        raise KeepaliveError("После нажатия «Войти» страница осталась на форме входа") from exc
    page.wait_for_timeout(4_000)
    if SIGNIN_MARKER in page.url:
        raise KeepaliveError("Ozon снова вернул форму входа - нужен вход вручную")


def _spread_cookies(session_path: Path, fresh: List[Dict[str, Any]], user_agent: Optional[str]) -> None:
    state = json.loads(session_path.read_text(encoding="utf-8"))
    previous = {cookie.get("name"): cookie for cookie in state.get("cookies") or []}
    merged = [cookie for cookie in fresh if cookie.get("name") not in COMPANY_COOKIES]
    merged.extend(previous[name] for name in COMPANY_COOKIES if name in previous)

    updated = copy.deepcopy(state)
    updated["cookies"] = merged
    session_path.write_text(json.dumps(updated, ensure_ascii=False), encoding="utf-8")
    if user_agent:
        save_session_user_agent(session_path, user_agent)
    _clear_session_needs_relogin(session_path)


def refresh_sessions(db_path: Path, *, cdp_port: int = DEFAULT_CDP_PORT) -> int:
    """Продлевает сессию в браузере и раскладывает свежие cookie по аккаунтам.

    Возвращает число обновлённых аккаунтов. Бросает KeepaliveError, если браузер
    не открыт или вход восстановить не удалось.
    """
    db = Database(str(db_path))
    try:
        db.ensure_schema()
        accounts = [dict(account) for account in db.list_accounts()]
    finally:
        db.close()
    if not accounts:
        return 0

    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.connect_over_cdp(_cdp_url(cdp_port))
        except Exception as exc:
            raise KeepaliveError("Браузер входа не запущен - продлевать сессию нечем") from exc
        contexts = list(browser.contexts)
        if not contexts:
            raise KeepaliveError("В браузере нет ни одной вкладки")
        context = contexts[0]
        page = _seller_page(context)
        _open_reviews_page(page)
        fresh = context.cookies()
        try:
            user_agent = page.evaluate("() => navigator.userAgent")
        except Exception:
            user_agent = None

    if not any(cookie.get("name") == "__Secure-access-token" for cookie in fresh):
        raise KeepaliveError("В браузере нет токена доступа")

    updated = 0
    for account in accounts:
        session_path = Path(account["session_path"] or "")
        if not session_path.name or not session_path.exists():
            continue
        try:
            _spread_cookies(session_path, fresh, user_agent)
            updated += 1
        except Exception:
            logger.exception("Не удалось обновить сессию аккаунта %s", account["id"])
    return updated


def _mark_all_relogin(db_path: Path, reason: str) -> None:
    db = Database(str(db_path))
    try:
        db.ensure_schema()
        accounts = [dict(account) for account in db.list_accounts()]
    finally:
        db.close()
    for account in accounts:
        session_path = Path(account["session_path"] or "")
        if session_path.name and session_path.exists():
            _mark_session_needs_relogin(session_path, reason)


class SessionKeepalive(QObject):
    """Раз в несколько минут продлевает сессию Ozon.

    Проверяет чаще, чем продлевает: если API уже уперся в 401 и рядом с сессией
    появился маркер, ждать очередного круга незачем.
    """

    refreshed = pyqtSignal(int)
    failed = pyqtSignal(str)

    def __init__(
        self,
        db_path: Path,
        check_interval_ms: int = 5 * 60_000,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._db_path = Path(db_path)
        self._timer = QTimer(self)
        self._timer.setInterval(check_interval_ms)
        self._timer.timeout.connect(self.poll)
        self._lock = threading.Lock()
        self._inflight = False
        self._last_success = 0.0
        self._last_failure_logged = ""

    def start(self, immediate: bool = False) -> None:
        self._timer.start()
        if immediate:
            self.poll()

    def _refresh_minutes(self) -> int:
        db = Database(str(self._db_path))
        try:
            db.ensure_schema()
            raw = db.get_setting("session_refresh_minutes")
        except Exception:
            raw = None
        finally:
            db.close()
        try:
            return max(1, int(raw))
        except (TypeError, ValueError):
            return DEFAULT_REFRESH_MINUTES

    def _session_is_stale(self) -> bool:
        db = Database(str(self._db_path))
        try:
            db.ensure_schema()
            accounts = [dict(account) for account in db.list_accounts()]
        except Exception:
            return False
        finally:
            db.close()
        for account in accounts:
            session_path = Path(account["session_path"] or "")
            if session_path.name and session_path.exists() and _session_needs_relogin(session_path):
                return True
        return False

    def poll(self) -> None:
        with self._lock:
            if self._inflight:
                return
            self._inflight = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        try:
            due = (time.time() - self._last_success) >= self._refresh_minutes() * 60
            if not due and not self._session_is_stale():
                return
            updated = refresh_sessions(self._db_path)
            self._last_success = time.time()
            self._last_failure_logged = ""
            if updated:
                logger.info("Сессия Ozon продлена, обновлено аккаунтов: %s", updated)
            self.refreshed.emit(updated)
        except KeepaliveError as exc:
            message = str(exc)
            # Одну и ту же причину в лог пишем один раз, иначе он захлебнётся.
            if message != self._last_failure_logged:
                logger.warning("Продлить сессию Ozon не удалось: %s", message)
                self._last_failure_logged = message
            _mark_all_relogin(self._db_path, f"keepalive: {message}")
            self.failed.emit(message)
        except Exception:
            logger.exception("Сбой продления сессии Ozon")
        finally:
            with self._lock:
                self._inflight = False
