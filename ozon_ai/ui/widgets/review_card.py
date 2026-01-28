from typing import Any, Dict

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)


class ReviewCard(QFrame):
    sent = pyqtSignal(str, str)

    def __init__(self, review: Dict[str, Any], editable: bool = True) -> None:
        super().__init__()
        self.review = review
        self.setObjectName("ReviewCard")
        self.setFrameShape(QFrame.Shape.NoFrame)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel(review.get("product_title") or "Без названия")
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        title.setWordWrap(True)
        header.addWidget(title, 1)

        rating = QLabel(f"{review.get('rating', '-')}")
        rating.setObjectName("RatingBadge")
        header.addWidget(rating)
        layout.addLayout(header)

        meta_parts = [
            f"SKU: {review.get('sku')}",
            f"Бренд: {review.get('brand_name')}",
            f"Дата: {review.get('published_at')}",
        ]
        meta = QLabel(" | ".join(part for part in meta_parts if part))
        meta.setObjectName("MetaText")
        meta.setWordWrap(True)
        layout.addWidget(meta)

        text = review.get("text") or "(Нет текста отзыва)"
        review_label = QLabel(f"Отзыв: {text}")
        review_label.setWordWrap(True)
        layout.addWidget(review_label)

        layout.addWidget(QLabel("Ответ ИИ:"))
        response_value = review.get("ai_response") or ""
        if not editable:
            response_value = review.get("user_response") or response_value
        self.response_edit = QPlainTextEdit()
        self.response_edit.setPlainText(response_value)
        self.response_edit.setReadOnly(not editable)
        self.response_edit.setMinimumHeight(90)
        layout.addWidget(self.response_edit)

        self.status_label = QLabel()
        self.status_label.setObjectName("StatusLabel")
        layout.addWidget(self.status_label)

        button_row = QHBoxLayout()
        button_row.addStretch(1)
        self.send_button = QPushButton("Отправить ответ")
        self.send_button.clicked.connect(self._handle_send)
        self.send_button.setEnabled(editable)
        if not editable:
            self.status_label.setText("Отправлено")
        button_row.addWidget(self.send_button)
        layout.addLayout(button_row)

    def _handle_send(self) -> None:
        response = self.response_edit.toPlainText().strip()
        if not response:
            QMessageBox.warning(self, "Пустой ответ", "Введите ответ перед отправкой.")
            return
        self.sent.emit(self.review.get("uuid"), response)
