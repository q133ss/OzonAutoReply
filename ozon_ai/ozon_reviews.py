import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


REVIEW_LIST_URL = "https://seller.ozon.ru/api/v4/review/list"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/144.0.0.0 Safari/537.36"
)
DEFAULT_FILTER = {"published_at": {}, "interaction_status": ["NOT_VIEWED"]}
DEFAULT_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ru",
    "Content-Type": "application/json",
    "Origin": "https://seller.ozon.ru",
    "Referer": "https://seller.ozon.ru/app/reviews",
}
DEFAULT_XO3_HEADERS = {
    "x-o3-app-name": "seller-ui",
    "x-o3-language": "ru",
    "x-o3-page-type": "review",
}
AUTH_MARKER_SUFFIX = ".relogin"


def _auth_marker_path(session_path: Path) -> Path:
    return session_path.with_suffix(session_path.suffix + AUTH_MARKER_SUFFIX)


def _mark_session_needs_relogin(session_path: Path, reason: str) -> None:
    try:
        _auth_marker_path(session_path).write_text(reason, encoding="utf-8")
    except Exception:
        logging.getLogger(__name__).exception("Failed to write relogin marker for %s", session_path)


def _clear_session_needs_relogin(session_path: Path) -> None:
    try:
        _auth_marker_path(session_path).unlink(missing_ok=True)
    except Exception:
        logging.getLogger(__name__).exception("Failed to remove relogin marker for %s", session_path)


def _looks_like_html(text: str) -> bool:
    if not text:
        return False
    sample = text.lstrip()[:200].lower()
    return "<html" in sample or "<!doctype" in sample or "</html>" in sample or "<script" in sample


def _is_auth_failure(status: int, body: Optional[str], content_type: Optional[str]) -> bool:
    if status in {401, 403}:
        return True
    if content_type and "text/html" in content_type.lower():
        return True
    if body and _looks_like_html(body):
        return True
    return False


def _session_needs_relogin(session_path: Path, storage_state: Optional[Dict[str, Any]] = None) -> bool:
    if _auth_marker_path(session_path).exists():
        return True
    if storage_state is None:
        storage_state = _load_storage_state(session_path) or {}
    cookies = storage_state.get("cookies") or []
    token_names = {"__Secure-access-token", "__Secure-refresh-token"}
    now = time.time()
    found_token = False
    for cookie in cookies:
        if cookie.get("name") not in token_names:
            continue
        found_token = True
        expires = cookie.get("expires")
        try:
            expires_value = float(expires)
        except (TypeError, ValueError):
            continue
        if expires_value > 0 and expires_value < now:
            return True
    return not found_token


def _load_storage_state(session_path: Path) -> Optional[Dict[str, Any]]:
    try:
        return json.loads(session_path.read_text(encoding="utf-8"))
    except Exception:
        logging.getLogger(__name__).exception("Failed to read session: %s", session_path)
        return None


def _extract_company_id(storage_state: Dict[str, Any]) -> Optional[str]:
    cookies = storage_state.get("cookies") or []
    for cookie in cookies:
        if cookie.get("name") == "sc_company_id" and cookie.get("value"):
            return str(cookie["value"])

    origins = storage_state.get("origins") or []
    for origin in origins:
        if origin.get("origin") != "https://seller.ozon.ru":
            continue
        for item in origin.get("localStorage") or []:
            if item.get("name") != "vuex":
                continue
            try:
                payload = json.loads(item.get("value") or "{}")
            except Exception:
                continue
            user = payload.get("user") or {}
            content_id = user.get("contentId") or user.get("content_id")
            if content_id:
                return str(content_id)
            company = payload.get("company") or {}
            content_id = company.get("contentId") or company.get("content_id")
            if content_id:
                return str(content_id)
    return None


def _find_latest_har(session_path: Path) -> Optional[Path]:
    candidates: List[Path] = []
    bases = [session_path.parent]
    bases.extend(list(session_path.parents[:4]))
    for base in bases:
        if base.exists():
            candidates.extend(base.glob("*.har"))
            har_dir = base / "data"
            if har_dir.exists():
                candidates.extend(har_dir.glob("*.har"))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def _load_review_template(har_path: Path) -> Tuple[Dict[str, str], Dict[str, Any], Optional[str], Optional[str]]:
    headers: Dict[str, str] = {}
    payload: Dict[str, Any] = {}
    company_id: Optional[str] = None
    user_agent: Optional[str] = None

    try:
        har_data = json.loads(har_path.read_text(encoding="utf-8"))
    except Exception:
        logging.getLogger(__name__).exception("Failed to read HAR: %s", har_path)
        return headers, payload, company_id, user_agent

    entries = har_data.get("log", {}).get("entries", [])
    for entry in entries:
        request = entry.get("request", {})
        if request.get("url") != REVIEW_LIST_URL:
            continue
        for header in request.get("headers", []):
            name = header.get("name")
            value = header.get("value")
            if not name or value is None:
                continue
            lower_name = name.lower()
            if lower_name.startswith("x-o3-") or lower_name in {
                "accept",
                "accept-language",
                "content-type",
                "origin",
                "referer",
                "user-agent",
                "sec-ch-ua",
                "sec-ch-ua-platform",
                "sec-ch-ua-mobile",
                "sec-fetch-site",
                "sec-fetch-mode",
                "sec-fetch-dest",
                "dnt",
                "pragma",
                "cache-control",
                "priority",
            }:
                headers[name] = value
        user_agent = headers.get("user-agent") or headers.get("User-Agent")
        post_data = request.get("postData", {}) or {}
        text = post_data.get("text")
        if text:
            try:
                payload = json.loads(text)
            except Exception:
                logging.getLogger(__name__).exception("Failed to parse HAR payload")
        company_id = (
            payload.get("company_id")
            or payload.get("companyId")
            or headers.get("x-o3-company-id")
            or headers.get("X-O3-Company-Id")
        )
        break

    return headers, payload, str(company_id) if company_id else None, user_agent


def _build_headers(
    company_id: str,
    template_headers: Dict[str, str],
    template_user_agent: Optional[str],
) -> Tuple[Dict[str, str], str]:
    headers: Dict[str, str] = {}
    seen: set[str] = set()

    def put(name: str, value: str) -> None:
        key = name.lower()
        if key in seen:
            for existing in list(headers):
                if existing.lower() == key:
                    headers.pop(existing, None)
                    break
        headers[name] = value
        seen.add(key)

    for name, value in {**DEFAULT_HEADERS, **DEFAULT_XO3_HEADERS}.items():
        put(name, value)

    for name, value in template_headers.items():
        if name.lower() == "cookie":
            continue
        put(name, value)

    put("x-o3-company-id", company_id)
    user_agent = template_user_agent or headers.get("user-agent") or headers.get("User-Agent") or USER_AGENT
    put("User-Agent", user_agent)
    return headers, user_agent


def _extract_reviews_payload(payload: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], bool, Optional[Dict[str, Any]]]:
    reviews: List[Dict[str, Any]] = []
    has_next = False
    last_review: Optional[Dict[str, Any]] = None

    if not isinstance(payload, dict):
        return reviews, has_next, last_review

    result = payload.get("result")
    if isinstance(result, list):
        reviews = result
        has_next = bool(payload.get("hasNext") or payload.get("has_next"))
        last_review = payload.get("last_review")
        return reviews, has_next, last_review

    if isinstance(result, dict):
        reviews = result.get("reviews") or result.get("items") or result.get("result") or []
        has_next = bool(result.get("hasNext") or result.get("has_next") or payload.get("hasNext") or payload.get("has_next"))
        last_review = result.get("last_review") or payload.get("last_review")
        return reviews, has_next, last_review

    reviews = payload.get("reviews") or []
    has_next = bool(payload.get("hasNext") or payload.get("has_next"))
    last_review = payload.get("last_review")
    return reviews, has_next, last_review


def fetch_all_new_reviews(session_path: Path, timeout: int = 20) -> List[Dict[str, Any]]:
    if not session_path.exists():
        return []

    storage_state = _load_storage_state(session_path)
    if not storage_state:
        return []

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
        logging.getLogger(__name__).warning("Missing company id in %s", session_path)
        return []

    headers, user_agent = _build_headers(company_id, template_headers, template_user_agent)
    filter_payload = template_payload.get("filter") if isinstance(template_payload, dict) else None
    base_payload: Dict[str, Any] = {
        "company_id": company_id,
        "company_type": template_payload.get("company_type", "seller"),
        "filter": filter_payload if isinstance(filter_payload, dict) else DEFAULT_FILTER,
    }

    reviews: Dict[str, Dict[str, Any]] = {}
    last_review: Optional[Dict[str, Any]] = None

    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except Exception:
        logging.getLogger(__name__).exception("Playwright not available")
        return []

    try:
        with sync_playwright() as playwright:
            request_context = playwright.request.new_context(
                storage_state=str(session_path),
                extra_http_headers=headers,
                user_agent=user_agent,
            )
            try:
                for _ in range(100):
                    payload = dict(base_payload)
                    if last_review:
                        payload["last_review"] = last_review
                    response = request_context.post(
                        REVIEW_LIST_URL,
                        data=json.dumps(payload),
                        timeout=timeout * 1000,
                    )
                    content_type = response.headers.get("content-type") or response.headers.get("Content-Type")
                    body_text: Optional[str] = None
                    if not response.ok:
                        body_text = response.text()
                        if _is_auth_failure(response.status, body_text, content_type):
                            _mark_session_needs_relogin(session_path, f"status={response.status}")
                        logging.getLogger(__name__).warning(
                            "Review request failed: status=%s body=%s",
                            response.status,
                            body_text,
                        )
                        break
                    try:
                        page = response.json()
                    except Exception:
                        body_text = body_text or response.text()
                        if _is_auth_failure(response.status, body_text, content_type):
                            _mark_session_needs_relogin(session_path, "invalid_json_html")
                        logging.getLogger(__name__).exception("Failed to parse review response JSON")
                        break
                    _clear_session_needs_relogin(session_path)
                    page_reviews, has_next, last_review = _extract_reviews_payload(page)
                    for review in page_reviews:
                        if not isinstance(review, dict):
                            continue
                        uuid = review.get("uuid")
                        if uuid:
                            reviews[uuid] = review
                    if not page_reviews or not has_next or not last_review:
                        break
            finally:
                request_context.dispose()
    except PlaywrightError as exc:
        logging.getLogger(__name__).warning("Playwright request failed: %s", exc)
    except Exception:
        logging.getLogger(__name__).exception("Failed to fetch reviews via Playwright")

    return list(reviews.values())
