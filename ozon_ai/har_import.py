import base64
import json
import logging
from pathlib import Path
from typing import Any, Dict, List


REVIEW_LIST_URL = "https://seller.ozon.ru/api/v4/review/list"


def load_reviews_from_har(har_path: Path) -> List[Dict[str, Any]]:
    if not har_path.exists():
        return []

    try:
        har_data = json.loads(har_path.read_text(encoding="utf-8"))
    except Exception:
        logging.getLogger(__name__).exception("Failed to read HAR: %s", har_path)
        return []

    entries = har_data.get("log", {}).get("entries", [])
    if not isinstance(entries, list):
        return []

    reviews: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        request = entry.get("request", {})
        url = request.get("url")
        if not url or not url.startswith(REVIEW_LIST_URL):
            continue
        response = entry.get("response", {})
        if response.get("status") and response.get("status") >= 400:
            continue
        content = response.get("content", {})
        text = content.get("text")
        if not text:
            continue
        if content.get("encoding") == "base64":
            try:
                text = base64.b64decode(text).decode("utf-8", errors="ignore")
            except Exception:
                logging.getLogger(__name__).exception("Failed to decode base64 HAR payload")
                continue
        try:
            payload = json.loads(text)
        except Exception:
            logging.getLogger(__name__).exception("Failed to parse HAR JSON payload")
            continue

        result = payload.get("result")
        if not isinstance(result, list):
            continue
        for review in result:
            if not isinstance(review, dict):
                continue
            uuid = review.get("uuid")
            if uuid:
                reviews[uuid] = review

    return list(reviews.values())
