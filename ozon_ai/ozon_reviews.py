import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REVIEW_LIST_URL = "https://seller.ozon.ru/api/v4/review/list"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/144.0.0.0 Safari/537.36"
)


def _load_session_cookies(session_path: Path) -> Tuple[str, Optional[str]]:
    try:
        data = json.loads(session_path.read_text(encoding="utf-8"))
    except Exception:
        logging.getLogger(__name__).exception("Failed to read session: %s", session_path)
        return "", None

    cookies = data.get("cookies") or []
    cookie_pairs: List[str] = []
    company_id: Optional[str] = None
    for cookie in cookies:
        name = cookie.get("name")
        value = cookie.get("value")
        if not name or value is None:
            continue
        domain = (cookie.get("domain") or "").lstrip(".")
        if domain.endswith("ozon.ru") or domain.endswith("ozone.ru"):
            cookie_pairs.append(f"{name}={value}")
        if name == "sc_company_id" and value:
            company_id = value

    return "; ".join(cookie_pairs), company_id


def _fetch_reviews_page(
    cookie_header: str,
    company_id: str,
    last_review: Optional[Dict[str, Any]] = None,
    timeout: int = 20,
) -> Optional[Dict[str, Any]]:
    payload: Dict[str, Any] = {
        "company_id": company_id,
        "company_type": "seller",
        "filter": {"published_at": {}, "interaction_status": ["NOT_VIEWED"]},
    }
    if last_review:
        payload["last_review"] = last_review

    body = json.dumps(payload).encode("utf-8")
    request = Request(REVIEW_LIST_URL, data=body, method="POST")
    request.add_header("Accept", "application/json, text/plain, */*")
    request.add_header("Content-Type", "application/json")
    request.add_header("Origin", "https://seller.ozon.ru")
    request.add_header("Referer", "https://seller.ozon.ru/app/reviews")
    request.add_header("User-Agent", USER_AGENT)
    request.add_header("x-o3-language", "ru")
    request.add_header("Cookie", cookie_header)

    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read().decode("utf-8", errors="ignore")
        return json.loads(data)
    except HTTPError as exc:
        logging.getLogger(__name__).warning("Review request failed: %s", exc)
    except URLError as exc:
        logging.getLogger(__name__).warning("Review request error: %s", exc)
    except Exception:
        logging.getLogger(__name__).exception("Failed to fetch reviews page")
    return None


def fetch_all_new_reviews(session_path: Path, timeout: int = 20) -> List[Dict[str, Any]]:
    if not session_path.exists():
        return []

    cookie_header, company_id = _load_session_cookies(session_path)
    if not cookie_header or not company_id:
        logging.getLogger(__name__).warning("Missing cookies or company id in %s", session_path)
        return []

    reviews: Dict[str, Dict[str, Any]] = {}
    last_review: Optional[Dict[str, Any]] = None
    for _ in range(100):
        page = _fetch_reviews_page(cookie_header, company_id, last_review, timeout=timeout)
        if not page:
            break
        page_reviews = page.get("result") or []
        for review in page_reviews:
            if not isinstance(review, dict):
                continue
            uuid = review.get("uuid")
            if uuid:
                reviews[uuid] = review
        if not page_reviews:
            break
        if not page.get("hasNext"):
            break
        last_review = page.get("last_review")
        if not last_review:
            break

    return list(reviews.values())
