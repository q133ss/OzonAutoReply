import json
import logging
import os
import random
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional
from urllib import error as url_error
from urllib import request as url_request

_DEFAULT_MODEL = "gpt-4o-mini"
_DEFAULT_TIMEOUT = 30
_BASE_URL = os.environ.get("OPENAI_BASE_URL") or os.environ.get("OPENAI_API_BASE") or "https://api.openai.com/v1"
_DOTENV_CACHE: Optional[Dict[str, str]] = None
_DOTENV_LOCK = threading.Lock()

_SYSTEM_PROMPT = (
    "You are a seller on a marketplace. Reply in Russian. "
    "The response must be send-ready and professional, without mentioning AI or templates. "
    "2-4 sentences, friendly and concise. "
    "If rating is 4-5: thank the customer and wish well. "
    "If rating is 3: thank and say you will improve. "
    "If rating is 1-2: apologize and offer a solution (return via marketplace or support). "
    "Do not use lists, quotes, or markdown. "
    "Ask at most one question. "
    "You may include at most one appropriate emoji."
)


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


def _fallback_response(review: Dict[str, Any]) -> str:
    rating = review.get("rating", 0) or 0
    text = (review.get("text") or "").strip()
    if rating >= 5 and not text:
        return "Спасибо за высокую оценку! Рады, что товар вам понравился."
    if rating >= 4:
        return (
            "Здравствуйте! Спасибо за ваш отзыв. Мы рады, что вы остались довольны качеством продукта. "
            "Если появятся вопросы, мы всегда готовы помочь! Желаем здоровья и удачи! 🌿"
        )
    if rating == 3:
        return "Спасибо за отзыв. Мы учтем ваши замечания, чтобы стать лучше."
    return (
        "Здравствуйте! Спасибо за ваш отзыв. Нам жаль, что товар не оправдал ожиданий. "
        "Пожалуйста, оформите возврат через маркетплейс, если есть дефекты. Мы передадим информацию для проверки качества 🌿"
    )


def _build_user_input(review: Dict[str, Any], examples: Optional[list[Dict[str, Any]]] = None) -> str:
    rating = review.get("rating", 0) or 0
    text = (review.get("text") or "").strip() or "[без текста]"
    product = review.get("product", {}) or {}
    title = (product.get("title") or "").strip()
    is_delivery = bool(review.get("is_delivery_review"))
    parts = [f"Оценка: {rating}/5.", f"Текст отзыва: {text}"]
    if title:
        parts.append(f"Товар: {title}.")
    if is_delivery:
        parts.append("Отзыв относится к доставке.")
    if examples:
        formatted = []
        for idx, example in enumerate(examples, start=1):
            ex_title = (example.get("product_title") or "").strip()
            ex_rating = example.get("rating")
            ex_text = (example.get("text") or "").strip()
            ex_answer = (example.get("example_response") or "").strip()
            if not ex_text or not ex_answer:
                continue
            chunk = [f"Пример {idx}."]
            if ex_title:
                chunk.append(f"Товар: {ex_title}.")
            if ex_rating:
                chunk.append(f"Оценка: {ex_rating}/5.")
            chunk.append(f"Отзыв: {ex_text}")
            chunk.append(f"Ответ: {ex_answer}")
            formatted.append(" ".join(chunk))
        if formatted:
            parts.append("Примеры ответов (не копировать дословно, придерживаться стиля):")
            parts.extend(formatted)
    return " ".join(parts)


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


def _call_openai(api_key: str, model: str, prompt: str, timeout: int) -> str:
    payload = {
        "model": model,
        "input": prompt,
        "instructions": _SYSTEM_PROMPT,
        "temperature": 0.4,
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
    min_interval: int = 10,
    max_interval: int = 30,
    timeout: int = _DEFAULT_TIMEOUT,
) -> str:
    api_key = api_key or get_openai_api_key()
    if not api_key:
        return _fallback_response(review)

    model = model or get_openai_model()
    prompt = _build_user_input(review, examples=examples)
    logger = logging.getLogger(__name__)

    _rate_limiter.throttle(min_interval, max_interval)
    try:
        text = _call_openai(api_key, model, prompt, timeout)
        text = _postprocess(text)
        if text:
            return text
        logger.warning("Empty OpenAI response, using fallback")
    except url_error.HTTPError as exc:
        try:
            details = exc.read().decode("utf-8", errors="ignore")
        except Exception:
            details = ""
        logger.warning("OpenAI HTTP error: %s %s", exc, details)
    except Exception:
        logger.exception("Failed to generate OpenAI response")
    return _fallback_response(review)
