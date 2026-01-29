import logging
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QLabel, QScrollArea, QTabWidget, QVBoxLayout, QWidget, QMessageBox, QFrame

from ...db import Database
from ...ozon_comments import send_review_comment
from ..widgets.review_card import ReviewCard
from ..widgets.review_list import ReviewList


class ReviewsTab(QWidget):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self._logger = logging.getLogger("ui.reviews")
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
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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
        review = self.db.get_review(uuid)
        if not review:
            QMessageBox.warning(self, "Ошибка", "Не удалось найти отзыв для отправки.")
            return
        session_path = self._resolve_session_path(review)
        if not session_path or not session_path.exists():
            QMessageBox.warning(self, "Ошибка", "Не найден файл сессии для отправки ответа.")
            return

        send_interval = int(self.db.get_setting("send_interval") or 5)

        def worker() -> None:
            ok = False
            try:
                ok = send_review_comment(
                    session_path,
                    uuid,
                    response,
                    throttle_interval=send_interval,
                )
            except Exception:
                self._logger.exception("Failed to send review response")

            def finish() -> None:
                if ok:
                    self.db.update_review_status(uuid, "completed", response)
                    QMessageBox.information(self, "Отправлено", "Ответ отправлен. Отзыв перемещен в завершенные.")
                    self.refresh()
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось отправить ответ. Проверьте сессию.")

            QTimer.singleShot(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def _resolve_session_path(self, review: Dict[str, Any]) -> Optional[Path]:
        account_id = review.get("account_id")
        if account_id:
            try:
                account = self.db.get_account(int(account_id))
            except Exception:
                account = None
            if account and account["session_path"]:
                return Path(account["session_path"])
        accounts = self.db.list_accounts()
        if len(accounts) == 1 and accounts[0]["session_path"]:
            return Path(accounts[0]["session_path"])
        return None
