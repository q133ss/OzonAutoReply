import os
import sys
from argparse import ArgumentParser
from pathlib import Path

from ozon_ai.com_runtime import bootstrap_windows_com
from ozon_ai.main import main


def _ensure_frozen_env() -> None:
    if getattr(sys, "frozen", False):
        base_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(base_dir / "playwright-browsers"))


def _run_playwright_runner() -> None:
    from ozon_ai.playwright_runner import main as runner_main

    idx = sys.argv.index("--run-playwright-runner")
    sys.argv = [sys.argv[0]] + sys.argv[idx + 1 :]
    raise SystemExit(runner_main())


def _show_message(title: str, message: str, *, is_error: bool = False) -> None:
    try:
        import ctypes

        flags = 0x10 if is_error else 0x40
        ctypes.windll.user32.MessageBoxW(None, message, title, flags)
    except Exception:
        pass


def _run_list_accounts() -> None:
    from ozon_ai.real_browser_session import format_accounts

    message = format_accounts()
    print(message)
    _show_message("OzonAutoReply Accounts", message)


def _run_open_real_browser() -> None:
    from ozon_ai.real_browser_session import OZON_REVIEWS_URL, open_real_browser

    parser = ArgumentParser(add_help=False)
    parser.add_argument("--open-real-browser", action="store_true")
    parser.add_argument("--port", type=int, default=9222)
    parser.add_argument("--url", default=OZON_REVIEWS_URL)
    args, _ = parser.parse_known_args(sys.argv[1:])

    browser_path, profile_dir = open_real_browser(port=args.port, start_url=args.url)
    message = (
        "Открыт реальный браузер без Playwright-автоматизации.\n\n"
        f"Браузер: {browser_path}\n"
        f"Профиль: {profile_dir}\n"
        f"CDP порт: {args.port}\n\n"
        "Дальше:\n"
        "1. Войдите в Ozon в открывшемся окне.\n"
        "2. Откройте seller.ozon.ru/app/reviews в этом же окне.\n"
        "3. Не закрывая браузер, запустите импорт сессии."
    )
    print(message)
    _show_message("OzonAutoReply", message)


def _run_import_session_from_browser() -> None:
    from ozon_ai.real_browser_session import import_session_from_browser

    parser = ArgumentParser(add_help=False)
    parser.add_argument("--import-session-from-browser", action="store_true")
    parser.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    parser.add_argument("--account-id", type=int)
    parser.add_argument("--name", default="")
    args, _ = parser.parse_known_args(sys.argv[1:])

    result = import_session_from_browser(
        cdp_url=args.cdp_url,
        account_id=args.account_id,
        account_name=args.name,
    )
    message = (
        "Сессия импортирована.\n\n"
        f"Аккаунт: {result.account_name or '<new>'}\n"
        f"ID: {result.account_id if result.account_id is not None else '<new>'}\n"
        f"Файл сессии: {result.session_path}\n"
        f"company_id: {result.company_id or '<missing>'}\n"
        f"needs_relogin: {result.needs_relogin}"
    )
    if result.needs_relogin or not result.company_id:
        message += (
            "\n\nСессия сохранена, но выглядит неполной. "
            "Откройте seller.ozon.ru/app/reviews в том же браузере и повторите импорт."
        )
    print(message)
    _show_message("OzonAutoReply", message, is_error=bool(result.needs_relogin or not result.company_id))


def _run_test_openai() -> None:
    from ozon_ai.ai import get_openai_api_key, get_openai_model, test_openai_connection
    from ozon_ai.app_paths import db_path as app_db_path
    from ozon_ai.db import Database
    from ozon_ai.proxy import ProxyConfig

    parser = ArgumentParser(add_help=False)
    parser.add_argument("--test-openai", action="store_true")
    parser.add_argument("--no-proxy", action="store_true")
    parser.add_argument("--timeout", type=int, default=30)
    args, _ = parser.parse_known_args(sys.argv[1:])

    db = Database(str(app_db_path()))
    try:
        db.ensure_schema()
        api_key = get_openai_api_key() or db.get_setting("openai_api_key")
        proxy_config = None if args.no_proxy else ProxyConfig.from_db(db)
    finally:
        db.close()

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not found in .env, environment, or ozon_ai.db.")

    result = test_openai_connection(
        api_key=api_key,
        model=get_openai_model(),
        timeout=max(5, int(args.timeout)),
        proxy_config=proxy_config,
    )
    lines = [
        f"base_url: {result['base_url']}",
        f"model: {result['model']}",
        f"proxy_enabled: {result['proxy_enabled']}",
        f"proxy_server: {result['proxy_server'] or '<none>'}",
        f"ipify_ip: {result['ipify_ip'] or '<unknown>'}",
        f"status_code: {result['status_code']}",
    ]
    if result["ok"]:
        lines.append(f"reply: {result['reply']}")
    else:
        lines.append(f"error: {result['error'] or '<empty response>'}")
    message = "\n".join(lines)
    print(message)
    _show_message("OzonAutoReply OpenAI Test", message, is_error=not bool(result["ok"]))


if __name__ == "__main__":
    _ensure_frozen_env()
    bootstrap_windows_com()
    try:
        if "--run-playwright-runner" in sys.argv:
            _run_playwright_runner()
        elif "--list-accounts" in sys.argv:
            _run_list_accounts()
        elif "--open-real-browser" in sys.argv:
            _run_open_real_browser()
        elif "--import-session-from-browser" in sys.argv:
            _run_import_session_from_browser()
        elif "--test-openai" in sys.argv:
            _run_test_openai()
        else:
            main()
    except Exception as exc:
        message = str(exc) or repr(exc)
        print(message, file=sys.stderr)
        _show_message("OzonAutoReply Error", message, is_error=True)
        raise
