import difflib
import json
import logging
import os
import random
import re
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib import error as url_error
from urllib import request as url_request

_DEFAULT_MODEL = "gpt-4o-mini"
_DEFAULT_TIMEOUT = 30
_DEFAULT_TEMPERATURE = 1.0
_DEFAULT_TOP_P = 0.9
_DEFAULT_PRESENCE_PENALTY = 0.6
_DEFAULT_FREQUENCY_PENALTY = 0.3
_BASE_URL = os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE") or "https://api.openai.com/v1"
_DOTENV_CACHE: Optional[Dict[str, str]] = None
_DOTENV_LOCK = threading.Lock()

_SYSTEM_PROMPT = (
    "Ты продавец на маркетплейсе. Отвечай по-русски естественно, как человек. "
    "Никаких шаблонов, канцелярита и одинаковых фраз. Не используй клише вроде "
    "«Здравствуйте! Спасибо за ваш отзыв», «Мы рады, что вы остались довольны», "
    "«Если появятся вопросы, мы всегда готовы помочь», «Желаем здоровья и удачи». "
    "Не упоминай ИИ, шаблоны, правила или инструкции. "
    "1-3 коротких предложения, дружелюбно и по делу. "
    "Не используй списки, цитаты или разметку. "
    "Можно 0-1 уместный эмодзи. "
    "Опирайся на детали отзыва, товара, бренда или доставки. "
    "Если оценка 4-5: мягко отметь положительный опыт. "
    "Если оценка 3: поблагодари и скажи, что учтёте замечания. "
    "Если оценка 1-2: извинись и предложи решение (возврат через маркетплейс или поддержку). "
    "Задай не более одного вопроса и только если это действительно помогает."
)

_STYLE_HINTS = [
    "тепло и по-доброму",
    "коротко и уверенно",
    "нейтрально и уважительно",
    "с лёгкой заботой",
    "просто и без официоза",
    "спокойно и доброжелательно",
    "лаконично и по делу",
]


class _RateLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._next_time = 0.0

    def throttle(self, min_interval: int, max_interval: int) -> None:
        min_val = max(0, int(min_interval))
        max_val = max(min_val, int(max_interval))
        delay = random.uniform(min_val, max_val) if max_val else 0
        with self._lock:
            now = time.monotonic()
            if now < self._next_time:
                time.sleep(self._next_time - now)
            self._next_time = time.monotonic() + delay


_rate_limiter = _RateLimiter()


def _load_dotenv() -> Dict[str, str]:
    global _DOTENV_CACHE
    if _DOTENV_CACHE is not None:
        return _DOTENV_CACHE
    with _DOTENV_LOCK:
        if _DOTENV_CACHE is not None:
            return _DOTENV_CACHE
        env_path = Path(__file__).resolve().parent.parent / ".env"
        values: Dict[str, str] = {}
        if env_path.exists():
            try:
                for line in env_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key:
                        values[key] = value
            except Exception:
                logging.getLogger(__name__).exception("Failed to read .env")
        _DOTENV_CACHE = values
        return values


def get_openai_api_key() -> Optional[str]:
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key
    return _load_dotenv().get("OPENAI_API_KEY")


def get_openai_model() -> str:
    return os.environ.get("OPENAI_MODEL") or _load_dotenv().get("OPENAI_MODEL") or _DEFAULT_MODEL


def _build_user_input(
    review: Dict[str, Any],
    examples: Optional[list[Dict[str, Any]]] = None,
    style_hint: Optional[str] = None,
    style_seed: Optional[int] = None,
) -> str:
    rating = review.get("rating", 0) or 0
    text = (review.get("text") or "").strip() or "[no text]"
    product = review.get("product", {}) or {}
    title = (product.get("title") or "").strip()
    brand = (product.get("brand_info") or {}).get("name") or ""
    is_delivery = bool(review.get("is_delivery_review"))
    parts = [f"Rating: {rating}/5.", f"Review text: {text}"]
    if title:
        parts.append(f"Product: {title}.")
    if brand:
        parts.append(f"Brand: {brand}.")
    if is_delivery:
        parts.append("The review is about delivery.")
    if style_hint:
        parts.append(f"Style hint (do not include in the reply): {style_hint}.")
    if style_seed is not None:
        parts.append(f"Variation seed (do not include in the reply): {style_seed}.")
    if examples:
        formatted = []
        for idx, example in enumerate(examples, start=1):
            ex_title = (example.get("product_title") or "").strip()
            ex_rating = example.get("rating")
            ex_text = (example.get("text") or "").strip()
            ex_answer = (example.get("example_response") or "").strip()
            if not ex_text or not ex_answer:
                continue
            chunk = [f"Example {idx}."]
            if ex_title:
                chunk.append(f"Product: {ex_title}.")
            if ex_rating:
                chunk.append(f"Rating: {ex_rating}/5.")
            chunk.append(f"Review: {ex_text}")
            chunk.append(f"Reply: {ex_answer}")
            formatted.append(" ".join(chunk))
        if formatted:
            parts.append("Style examples (do not copy verbatim, avoid repeating phrases):")
            parts.extend(formatted)
    return " ".join(parts)



def _normalize_text(text: str) -> str:
    cleaned = text.lower().strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[^\w\s]", "", cleaned, flags=re.UNICODE)
    return cleaned


def _is_too_similar(text: str, recent: list[str], threshold: float = 0.85) -> bool:
    if not text:
        return True
    norm = _normalize_text(text)
    for item in recent:
        if not item:
            continue
        other = _normalize_text(item)
        if not other:
            continue
        if norm == other:
            return True
        ratio = difflib.SequenceMatcher(None, norm, other).ratio()
        if ratio >= threshold:
            return True
    return False


def _extract_output_text(payload: Dict[str, Any]) -> str:
    if isinstance(payload, dict):
        output_text = payload.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text
        for item in payload.get("output", []) or []:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "message":
                continue
            for content in item.get("content", []) or []:
                if not isinstance(content, dict):
                    continue
                if content.get("type") in {"output_text", "text"}:
                    text = content.get("text")
                    if isinstance(text, str) and text.strip():
                        return text
    return ""


def _postprocess(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith('"') and cleaned.endswith('"') and len(cleaned) > 1:
        cleaned = cleaned[1:-1].strip()
    if cleaned.startswith("“") and cleaned.endswith("”") and len(cleaned) > 1:
        cleaned = cleaned[1:-1].strip()
    return cleaned


def _call_openai(
    api_key: str,
    model: str,
    prompt: str,
    timeout: int,
    temperature: float,
    top_p: float,
    presence_penalty: float,
    frequency_penalty: float,
) -> str:
    payload = {
        "model": model,
        "input": prompt,
        "instructions": _SYSTEM_PROMPT,
        "temperature": temperature,
        "top_p": top_p,
        "presence_penalty": presence_penalty,
        "frequency_penalty": frequency_penalty,
        "max_output_tokens": 200,
    }
    url = f"{_BASE_URL}/responses"
    data = json.dumps(payload).encode("utf-8")
    req = url_request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with url_request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
    payload = json.loads(body)
    return _extract_output_text(payload)


def generate_ai_response(
    review: Dict[str, Any],
    *,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    examples: Optional[list[Dict[str, Any]]] = None,
    avoid_responses: Optional[list[str]] = None,
    max_attempts: int = 5,
    min_interval: int = 10,
    max_interval: int = 30,
    timeout: int = _DEFAULT_TIMEOUT,
) -> str:
    api_key = api_key or get_openai_api_key()
    if not api_key:
        return ""

    model = model or get_openai_model()
    logger = logging.getLogger(__name__)
    temperature = float(os.environ.get("OPENAI_TEMPERATURE") or _DEFAULT_TEMPERATURE)
    top_p = float(os.environ.get("OPENAI_TOP_P") or _DEFAULT_TOP_P)
    presence_penalty = float(os.environ.get("OPENAI_PRESENCE_PENALTY") or _DEFAULT_PRESENCE_PENALTY)
    frequency_penalty = float(os.environ.get("OPENAI_FREQUENCY_PENALTY") or _DEFAULT_FREQUENCY_PENALTY)
    recent = list(avoid_responses or [])

    for attempt in range(max(1, int(max_attempts))):
        style_hint = random.choice(_STYLE_HINTS)
        style_seed = random.randint(1000, 9999)
        prompt = _build_user_input(
            review,
            examples=examples,
            style_hint=style_hint,
            style_seed=style_seed,
        )
        _rate_limiter.throttle(min_interval, max_interval)
        try:
            text = _call_openai(
                api_key,
                model,
                prompt,
                timeout,
                temperature=temperature,
                top_p=top_p,
                presence_penalty=presence_penalty,
                frequency_penalty=frequency_penalty,
            )
            text = _postprocess(text)
        except url_error.HTTPError as exc:
            try:
                details = exc.read().decode("utf-8", errors="ignore")
            except Exception:
                details = ""
            logger.warning("OpenAI HTTP error: %s %s", exc, details)
            return ""
        except Exception:
            logger.exception("Failed to generate OpenAI response")
            return ""

        if not text:
            logger.warning("Empty OpenAI response")
            continue
        if recent and _is_too_similar(text, recent):
            logger.info("OpenAI response too similar, retrying")
            continue
        return text
    return ""
