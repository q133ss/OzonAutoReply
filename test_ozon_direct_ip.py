import json
import shutil
import tempfile
import time
from pathlib import Path

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth


CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OZON_LOGIN_URL = (
    "https://seller.ozon.ru/app/registration/signin?"
    "redirect=L3Jldmlld3M%2FX19ycj0xJmFidF9hdHQ9MQ%3D%3D"
)


def main() -> int:
    profile_dir = Path(tempfile.mkdtemp(prefix="ozon-direct-ip-check-"))
    result = {
        "mode": "direct_ip_installed_chrome",
        "chrome_path": CHROME_PATH,
    }
    try:
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                str(profile_dir),
                executable_path=CHROME_PATH,
                headless=False,
                ignore_default_args=["--enable-automation"],
                locale="ru-RU",
                timezone_id="Europe/Moscow",
                color_scheme="light",
                viewport={"width": 1440, "height": 900},
                screen={"width": 1440, "height": 900},
                args=[
                    "--start-maximized",
                    "--disable-blink-features=AutomationControlled",
                    "--accept-lang=ru-RU,ru",
                ],
                extra_http_headers={"Accept-Language": "ru-RU,ru;q=0.9"},
            )
            try:
                Stealth(navigator_languages_override=("ru-RU", "ru")).apply_stealth_sync(context)
                page = context.pages[0] if context.pages else context.new_page()
                page.set_default_timeout(30_000)

                page.goto("https://api.ipify.org?format=json", wait_until="domcontentloaded", timeout=30_000)
                ip_body = page.locator("body").inner_text(timeout=10_000).strip()
                result["exit_ip_raw"] = ip_body
                try:
                    result["exit_ip"] = json.loads(ip_body).get("ip")
                except Exception:
                    result["exit_ip"] = None

                page.goto(OZON_LOGIN_URL, wait_until="domcontentloaded", timeout=60_000)
                time.sleep(12)
                body_text = " ".join(page.locator("body").inner_text(timeout=15_000).split())
                title = page.title().strip()

                result["ozon_url"] = page.url
                result["ozon_title"] = title
                result["ozon_text_sample"] = body_text[:700]
                lower_text = body_text.lower()
                result["access_limited"] = "доступ ограничен" in lower_text or title.lower() == "доступ ограничен"
                result["looks_like_login"] = any(
                    token in lower_text for token in ["войти", "телефон", "email", "пароль", "код"]
                )

                incident = page.locator("#incident")
                if incident.count():
                    result["incident"] = incident.first.get_attribute("value")

                result["fingerprint"] = page.evaluate(
                    """() => ({
                        userAgent: navigator.userAgent,
                        webdriver: navigator.webdriver,
                        language: navigator.language,
                        languages: navigator.languages,
                        brands: navigator.userAgentData ? navigator.userAgentData.brands : null,
                        platform: navigator.platform,
                        hardwareConcurrency: navigator.hardwareConcurrency,
                        plugins: navigator.plugins.length
                    })"""
                )
            finally:
                context.close()
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("looks_like_login") and not result.get("access_limited"):
        print("\nRESULT: OK - Ozon login page opened on this IP.")
        return 0
    print("\nRESULT: BLOCKED - Ozon did not open the login page on this IP.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
