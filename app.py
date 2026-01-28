import json
import os
import sqlite3
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

SAMPLE_REVIEWS_JSON = r'''
[
    {
        "uuid": "019c0512-bf2d-719e-a742-85ed36e86f8c",
        "product": {
            "title": "Сода природная пищевая Baking Soda, добывается водным способом из содовых озер, для лечения организма, пышной выпечки, 501 г",
            "url": "https://www.ozon.ru/product/496029237/",
            "offer_id": "SOD501",
            "cover_image": "https://cdn1.ozone.ru/s3/multimedia-1-s/7946842060.jpg",
            "sku": "496029237",
            "brand_info": {
                "id": "100089762",
                "name": "ALUNA"
            }
        },
        "orderDeliveryType": "REVIEW_ORDER_DELIVERY_DONE",
        "text": "",
        "interaction_status": "NOT_VIEWED",
        "rating": 5,
        "photos_count": 0,
        "videos_count": 0,
        "comments_count": 0,
        "published_at": "2026-01-28T14:47:20.996265Z",
        "is_pinned": false,
        "is_quality_control": false,
        "chat_url": "https://seller.ozon.ru/app/messenger?channel=CS&context=reviewChat&prefillMessage=0JfQtNGA0LDQstGB0YLQstGD0LnRgtC1ISDQodC%2F0LDRgdC40LHQviwg0YfRgtC+INC%2F0L7QtNC10LvQuNC70LjRgdGMINCy0L%2FQtdGH0LDRgtC70LXQvdC40Y%2FQvNC4INC+INGC0L7QstCw0YDQtS4%3D&review_uuid=019c0512-bf2d-719e-a742-85ed36e86f8c&seller_id=128326&sku=496029237&url_sign=2zg4uo4AVnNeBNfPIVecKz8yU0UQkPN0ds8eOP6PwiY.6d705490.WyJyZXZpZXdfdXVpZCIsInVzZXJfaWQiLCJzZWxsZXJfaWQiLCJjaGFubmVsIl0.1&user_id=10144650",
        "is_delivery_review": false
    },
    {
        "uuid": "019c04ff-5952-7536-8247-cd1a122bd8e3",
        "product": {
            "title": "Сода природная пищевая Baking Soda, добывается водным способом из содовых озер, для лечения организма, пышной выпечки, 501 г",
            "url": "https://www.ozon.ru/product/496029237/",
            "offer_id": "SOD501",
            "cover_image": "https://cdn1.ozone.ru/s3/multimedia-1-s/7946842060.jpg",
            "sku": "496029237",
            "brand_info": {
                "id": "100089762",
                "name": "ALUNA"
            }
        },
        "orderDeliveryType": "REVIEW_ORDER_DELIVERY_DONE",
        "text": "",
        "interaction_status": "NOT_VIEWED",
        "rating": 5,
        "photos_count": 0,
        "videos_count": 0,
        "comments_count": 0,
        "published_at": "2026-01-28T14:26:09.576730Z",
        "is_pinned": false,
        "is_quality_control": false,
        "chat_url": "https://seller.ozon.ru/app/messenger?channel=CS&context=reviewChat&prefillMessage=0JfQtNGA0LDQstGB0YLQstGD0LnRgtC1ISDQodC%2F0LDRgdC40LHQviwg0YfRgtC+INC%2F0L7QtNC10LvQuNC70LjRgdGMINCy0L%2FQtdGH0LDRgtC70LXQvdC40Y%2FQvNC4INC+INGC0L7QstCw0YDQtS4%3D&review_uuid=019c04ff-5952-7536-8247-cd1a122bd8e3&seller_id=128326&sku=496029237&url_sign=VG2vyReuz8MTNZ_JXEBbj68vtNHXDSEDOSTj4qiq4p4.6d705490.WyJyZXZpZXdfdXVpZCIsInVzZXJfaWQiLCJzZWxsZXJfaWQiLCJjaGFubmVsIl0.1&user_id=34598629",
        "is_delivery_review": false
    },
    {
        "uuid": "019c04fc-2dab-7ddf-8ce8-97e4a63c3693",
        "product": {
            "title": "Сода природная пищевая Baking Soda, добывается водным способом из содовых озер, для лечения организма, пышной выпечки, 501 г",
            "url": "https://www.ozon.ru/product/496029237/",
            "offer_id": "SOD501",
            "cover_image": "https://cdn1.ozone.ru/s3/multimedia-1-s/7946842060.jpg",
            "sku": "496029237",
            "brand_info": {
                "id": "100089762",
                "name": "ALUNA"
            }
        },
        "orderDeliveryType": "REVIEW_ORDER_DELIVERY_DONE",
        "text": "",
        "interaction_status": "NOT_VIEWED",
        "rating": 5,
        "photos_count": 0,
        "videos_count": 0,
        "comments_count": 0,
        "published_at": "2026-01-28T14:22:41.765711Z",
        "is_pinned": false,
        "is_quality_control": false,
        "chat_url": "https://seller.ozon.ru/app/messenger?channel=CS&context=reviewChat&prefillMessage=0JfQtNGA0LDQstGB0YLQstGD0LnRgtC1ISDQodC%2F0LDRgdC40LHQviwg0YfRgtC+INC%2F0L7QtNC10LvQuNC70LjRgdGMINCy0L%2FQtdGH0LDRgtC70LXQvdC40Y%2FQvNC4INC+INGC0L7QstCw0YDQtS4%3D&review_uuid=019c04fc-2dab-7ddf-8ce8-97e4a63c3693&seller_id=128326&sku=496029237&url_sign=_fA7E0zqHlFKLnsP77S5i0iUIJubLrXco7q1RQlZRrM.6d705490.WyJyZXZpZXdfdXVpZCIsInVzZXJfaWQiLCJzZWxsZXJfaWQiLCJjaGFubmVsIl0.1&user_id=28649418",
        "is_delivery_review": false
    },
    {
        "uuid": "019c04cd-5c16-7540-aae7-7f74b9dbf0e3",
        "product": {
            "title": "Каолиновая белая глина пищевая премиальная, каолин Aluna Mori очищенный активированный, 510г",
            "url": "https://www.ozon.ru/product/1947442132/",
            "offer_id": "KAO510",
            "cover_image": "https://cdn1.ozone.ru/s3/multimedia-1-q/7556677982.jpg",
            "sku": "1947442132",
            "brand_info": {
                "id": "100210232",
                "name": "ALUNA MORI"
            }
        },
        "orderDeliveryType": "REVIEW_ORDER_DELIVERY_DONE",
        "text": "",
        "interaction_status": "NOT_VIEWED",
        "rating": 5,
        "photos_count": 0,
        "videos_count": 0,
        "comments_count": 0,
        "published_at": "2026-01-28T13:31:33.645441Z",
        "is_pinned": false,
        "is_quality_control": false,
        "chat_url": "https://seller.ozon.ru/app/messenger?channel=CS&context=reviewChat&prefillMessage=0JfQtNGA0LDQstGB0YLQstGD0LnRgtC1ISDQodC%2F0LDRgdC40LHQviwg0YfRgtC+INC%2F0L7QtNC10LvQuNC70LjRgdGMINCy0L%2FQtdGH0LDRgtC70LXQvdC40Y%2FQvNC4INC+INGC0L7QstCw0YDQtS4%3D&review_uuid=019c04cd-5c16-7540-aae7-7f74b9dbf0e3&seller_id=128326&sku=1947442132&url_sign=LNEkTT42jLwoUfUydZU110GosWAensOPuBBKkktHEHc.6d705490.WyJyZXZpZXdfdXVpZCIsInVzZXJfaWQiLCJzZWxsZXJfaWQiLCJjaGFubmVsIl0.1&user_id=123022888",
        "is_delivery_review": false
    },
    {
        "uuid": "019c04ca-4cdf-75a3-809c-3af46c4788bf",
        "product": {
            "title": "Диатомит пищевой для очищения организма, похудения, молодости, красоты и здоровья, природный, минеральный 2 пачки",
            "url": "https://www.ozon.ru/product/1711930918/",
            "offer_id": "DIA348NAT",
            "cover_image": "https://cdn1.ozone.ru/s3/multimedia-1-3/7406352111.jpg",
            "sku": "1711930918",
            "brand_info": {
                "id": "100210232",
                "name": "ALUNA MORI"
            }
        },
        "orderDeliveryType": "REVIEW_ORDER_DELIVERY_DONE",
        "text": "",
        "interaction_status": "NOT_VIEWED",
        "rating": 5,
        "photos_count": 0,
        "videos_count": 0,
        "comments_count": 0,
        "published_at": "2026-01-28T13:28:12.874223Z",
        "is_pinned": false,
        "is_quality_control": false,
        "chat_url": "",
        "is_delivery_review": false
    }
]
'''


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


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def ensure_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                uuid TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                product_title TEXT,
                product_url TEXT,
                offer_id TEXT,
                cover_image TEXT,
                sku TEXT,
                brand_id TEXT,
                brand_name TEXT,
                order_delivery_type TEXT,
                text TEXT,
                interaction_status TEXT,
                rating INTEGER,
                photos_count INTEGER,
                videos_count INTEGER,
                comments_count INTEGER,
                published_at TEXT,
                is_pinned INTEGER,
                is_quality_control INTEGER,
                chat_url TEXT,
                is_delivery_review INTEGER,
                ai_response TEXT,
                user_response TEXT
            )
            """
        )
        self.conn.commit()

    def get_setting(self, key: str) -> Optional[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else None

    def set_setting(self, key: str, value: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        self.conn.commit()

    def list_accounts(self) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, name FROM accounts ORDER BY id")
        return cur.fetchall()

    def add_account(self, name: str) -> None:
        cur = self.conn.cursor()
        cur.execute("INSERT INTO accounts (name) VALUES (?)", (name,))
        self.conn.commit()

    def delete_account(self, account_id: int) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        self.conn.commit()

    def count_reviews(self) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM reviews")
        return int(cur.fetchone()[0])

    def upsert_review(self, review: Dict[str, Any], status: str = "new") -> None:
        product = review.get("product", {})
        brand = product.get("brand_info", {})
        ai_response = review.get("ai_response") or generate_ai_response(review)
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO reviews (
                uuid, status, product_title, product_url, offer_id, cover_image, sku,
                brand_id, brand_name, order_delivery_type, text, interaction_status,
                rating, photos_count, videos_count, comments_count, published_at,
                is_pinned, is_quality_control, chat_url, is_delivery_review, ai_response, user_response
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT(uuid) DO UPDATE SET
                status = excluded.status,
                ai_response = excluded.ai_response
            """,
            (
                review.get("uuid"),
                status,
                product.get("title"),
                product.get("url"),
                product.get("offer_id"),
                product.get("cover_image"),
                product.get("sku"),
                brand.get("id"),
                brand.get("name"),
                review.get("orderDeliveryType"),
                review.get("text"),
                review.get("interaction_status"),
                review.get("rating"),
                review.get("photos_count"),
                review.get("videos_count"),
                review.get("comments_count"),
                review.get("published_at"),
                int(bool(review.get("is_pinned"))),
                int(bool(review.get("is_quality_control"))),
                review.get("chat_url"),
                int(bool(review.get("is_delivery_review"))),
                ai_response,
                review.get("user_response"),
            ),
        )
        self.conn.commit()

    def list_reviews(self, status: str) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM reviews WHERE status = ? ORDER BY published_at DESC
            """,
            (status,),
        )
        return [dict(row) for row in cur.fetchall()]

    def update_review_status(self, uuid: str, status: str, response: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE reviews SET status = ?, user_response = ? WHERE uuid = ?
            """,
            (status, response, uuid),
        )
        self.conn.commit()


class ApiKeyDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("OpenAI ключ")
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("sk-...")
        form.addRow("Введите OpenAI ключ:", self.key_input)

        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def key(self) -> str:
        return self.key_input.text().strip()

    def accept(self) -> None:
        if not self.key_input.text().strip():
            QMessageBox.warning(self, "Нужен ключ", "Введите ключ OpenAI, чтобы продолжить.")
            return
        super().accept()


class ReviewCard(QFrame):
    sent = pyqtSignal(str, str)

    def __init__(self, review: Dict[str, Any], editable: bool = True) -> None:
        super().__init__()
        self.review = review
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        self.setStyleSheet("QFrame { border-radius: 6px; }")

        layout = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel(review.get("product_title") or "Без названия")
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        title.setWordWrap(True)
        header.addWidget(title, 1)
        rating = QLabel(f"Оценка: {review.get('rating', '-')}")
        header.addWidget(rating)
        layout.addLayout(header)

        meta = QLabel(
            " | ".join(
                part
                for part in [
                    f"SKU: {review.get('sku')}",
                    f"Бренд: {review.get('brand_name')}",
                    f"Дата: {review.get('published_at')}",
                ]
                if part
            )
        )
        meta.setStyleSheet("color: #555;")
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
        layout.addWidget(self.response_edit)

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #2f6f2f;")
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


class ReviewList(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

    def clear(self) -> None:
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def add_card(self, card: QWidget) -> None:
        self.layout.addWidget(card)

    def finalize(self) -> None:
        self.layout.addStretch(1)


class ReviewsTab(QWidget):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.tabs = QTabWidget()
        self.new_tab = self._build_tab()
        self.done_tab = self._build_tab()
        self.tabs.addTab(self.new_tab["container"], "Новые")
        self.tabs.addTab(self.done_tab["container"], "Завершенные")

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        self.refresh()

    def _build_tab(self) -> Dict[str, Any]:
        container = QWidget()
        layout = QVBoxLayout(container)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        list_widget = ReviewList()
        scroll.setWidget(list_widget)
        layout.addWidget(scroll)
        return {"container": container, "list": list_widget}

    def refresh(self) -> None:
        self._populate(self.new_tab["list"], "new", editable=True)
        self._populate(self.done_tab["list"], "completed", editable=False)

    def _populate(self, list_widget: ReviewList, status: str, editable: bool) -> None:
        list_widget.clear()
        reviews = self.db.list_reviews(status)
        if not reviews:
            empty = QLabel("Нет отзывов")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            list_widget.add_card(empty)
            list_widget.finalize()
            return
        for review in reviews:
            card = ReviewCard(review, editable=editable)
            if editable:
                card.sent.connect(self._send_review)
            list_widget.add_card(card)
        list_widget.finalize()

    def _send_review(self, uuid: str, response: str) -> None:
        self.db.update_review_status(uuid, "completed", response)
        QMessageBox.information(self, "Отправлено", "Ответ отправлен. Отзыв перемещен в завершенные.")
        self.refresh()


class AccountsTab(QWidget):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        layout = QVBoxLayout(self)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        button_row = QHBoxLayout()
        self.add_button = QPushButton("Добавить аккаунт")
        self.add_button.clicked.connect(self._add_account)
        self.delete_button = QPushButton("Удалить аккаунт")
        self.delete_button.clicked.connect(self._delete_account)
        button_row.addWidget(self.add_button)
        button_row.addWidget(self.delete_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.refresh()

    def refresh(self) -> None:
        self.list_widget.clear()
        accounts = self.db.list_accounts()
        for account in accounts:
            item = QListWidgetItem(account["name"])
            item.setData(Qt.ItemDataRole.UserRole, account["id"])
            self.list_widget.addItem(item)

    def _add_account(self) -> None:
        QMessageBox.information(
            self,
            "Скоро",
            "Добавление аккаунта через Playwright будет доступно позже.",
        )

    def _delete_account(self) -> None:
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Нет выбора", "Выберите аккаунт для удаления.")
            return
        account_id = int(item.data(Qt.ItemDataRole.UserRole))
        self.db.delete_account(account_id)
        self.refresh()


class SettingsTab(QWidget):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("sk-...")

        self.min_interval = QSpinBox()
        self.min_interval.setRange(1, 3600)
        self.min_interval.setSuffix(" сек")

        self.max_interval = QSpinBox()
        self.max_interval.setRange(1, 3600)
        self.max_interval.setSuffix(" сек")

        form.addRow("OpenAI ключ:", self.api_key_input)
        form.addRow("Минимальный интервал:", self.min_interval)
        form.addRow("Максимальный интервал:", self.max_interval)

        layout.addLayout(form)
        self.save_button = QPushButton("Сохранить настройки")
        self.save_button.clicked.connect(self._save)
        layout.addWidget(self.save_button)
        layout.addStretch(1)

        self._load()

    def _load(self) -> None:
        api_key = self.db.get_setting("openai_api_key") or ""
        self.api_key_input.setText(api_key)
        min_interval = int(self.db.get_setting("min_interval") or 10)
        max_interval = int(self.db.get_setting("max_interval") or 30)
        self.min_interval.setValue(min_interval)
        self.max_interval.setValue(max_interval)

    def _save(self) -> None:
        min_val = self.min_interval.value()
        max_val = self.max_interval.value()
        if min_val > max_val:
            QMessageBox.warning(self, "Ошибка", "Минимальный интервал не может быть больше максимального.")
            return
        self.db.set_setting("openai_api_key", self.api_key_input.text().strip())
        self.db.set_setting("min_interval", str(min_val))
        self.db.set_setting("max_interval", str(max_val))
        QMessageBox.information(self, "Сохранено", "Настройки сохранены.")


class MainWindow(QMainWindow):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.setWindowTitle("Ozon автоответ")
        self.resize(1100, 750)

        tabs = QTabWidget()
        tabs.addTab(AccountsTab(db), "Аккаунты")
        tabs.addTab(ReviewsTab(db), "Отзывы")
        tabs.addTab(SettingsTab(db), "Настройки")
        self.setCentralWidget(tabs)


def ensure_defaults(db: Database) -> None:
    if db.get_setting("min_interval") is None:
        db.set_setting("min_interval", "10")
    if db.get_setting("max_interval") is None:
        db.set_setting("max_interval", "30")

    if db.count_reviews() == 0:
        reviews = json.loads(SAMPLE_REVIEWS_JSON)
        for review in reviews:
            db.upsert_review(review, status="new")


def main() -> None:
    app = QApplication(sys.argv)
    db_path = os.path.join(os.path.dirname(__file__), "ozon_ai.sqlite")
    db = Database(db_path)
    db.ensure_schema()
    ensure_defaults(db)

    api_key = db.get_setting("openai_api_key")
    if not api_key:
        dialog = ApiKeyDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            db.set_setting("openai_api_key", dialog.key())
        else:
            sys.exit(0)

    window = MainWindow(db)
    window.show()
    app.exec()
    db.close()


if __name__ == "__main__":
    main()
