import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .ozon_reviews import (
    _build_headers,
    _extract_company_id,
    _find_latest_har,
    _is_auth_failure,
    _mark_session_needs_relogin,
    _load_review_template,
    _load_storage_state,
    _clear_session_needs_relogin,
)


REVIEW_COMMENT_URL = "https://seller.ozon.ru/api/review/comment/create"


class _SendRateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._next_time = 0.0

    def throttle(self, interval: int) -> None:
        delay = max(0, int(interval))
        if delay <= 0:
            return
        with self._lock:
            now = time.monotonic()
            if now < self._next_time:
                time.sleep(self._next_time - now)
            self._next_time = time.monotonic() + delay


_rate_limiter = _SendRateLimiter()


def send_review_comment(
    session_path: Path,
    review_uuid: str,
    text: str,
    *,
    timeout: int = 20,
    throttle_interval: int = 0,
) -> bool:
    if not session_path.exists() or not review_uuid or not text:
        return False

    storage_state = _load_storage_state(session_path)
    if not storage_state:
        return False

    company_id = _extract_company_id(storage_state)
    template_headers: Dict[str, str] = {}
    template_payload: Dict[str, Any] = {}
    template_company_id: Optional[str] = None
    template_user_agent: Optional[str] = None

    har_path = _find_latest_har(session_path)
    if har_path:
        template_headers, template_payload, template_company_id, template_user_agent = _load_review_template(har_path)

    company_id = company_id or template_company_id
    if not company_id:
        logging.getLogger(__name__).warning("Missing company id for comment request (%s)", session_path)
        return False

    headers, user_agent = _build_headers(company_id, template_headers, template_user_agent)
    company_type = "seller"
    if isinstance(template_payload, dict):
        company_type = str(template_payload.get("company_type") or template_payload.get("companyType") or company_type)

    payload = {
        "company_id": company_id,
        "company_type": company_type,
        "text": text,
        "review_uuid": review_uuid,
    }

    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except Exception:
        logging.getLogger(__name__).exception("Playwright not available")
        return False

    if throttle_interval > 0:
        _rate_limiter.throttle(throttle_interval)

    try:
        with sync_playwright() as playwright:
            request_context = playwright.request.new_context(
                storage_state=str(session_path),
                extra_http_headers=headers,
                user_agent=user_agent,
            )
            try:
                response = request_context.post(
                    REVIEW_COMMENT_URL,
                    data=json.dumps(payload),
                    timeout=timeout * 1000,
                )
                content_type = response.headers.get("content-type") or response.headers.get("Content-Type")
                body_text: Optional[str] = None
                if not response.ok:
                    body_text = response.text()
                    if _is_auth_failure(response.status, body_text, content_type):
                        _mark_session_needs_relogin(session_path, f"comment_status={response.status}")
                    logging.getLogger(__name__).warning(
                        "Comment request failed: status=%s body=%s",
                        response.status,
                        body_text,
                    )
                    return False
                try:
                    payload = response.json()
                except Exception:
                    body_text = body_text or response.text()
                    if _is_auth_failure(response.status, body_text, content_type):
                        _mark_session_needs_relogin(session_path, "comment_invalid_json_html")
                        return False
                    return True
                if isinstance(payload, dict) and payload.get("error"):
                    logging.getLogger(__name__).warning("Comment request error: %s", payload.get("error"))
                    return False
                _clear_session_needs_relogin(session_path)
                return True
            finally:
                request_context.dispose()
    except PlaywrightError as exc:
        logging.getLogger(__name__).warning("Playwright comment request failed: %s", exc)
    except Exception:
        logging.getLogger(__name__).exception("Failed to send comment via Playwright")
    return False
