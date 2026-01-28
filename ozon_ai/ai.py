from typing import Any, Dict


def generate_ai_response(review: Dict[str, Any]) -> str:
    rating = review.get("rating", 0)
    text = (review.get("text") or "").strip()
    if rating >= 5 and not text:
        return "Спасибо за высокую оценку! Рады, что товар вам понравился."
    if rating >= 4:
        return "Спасибо за отзыв! Нам важно ваше мнение."
    if rating == 3:
        return "Спасибо за отзыв. Мы учтем ваши замечания, чтобы стать лучше."
    return "Сожалеем, что товар не оправдал ожиданий. Напишите, пожалуйста, подробнее, мы разберемся."
