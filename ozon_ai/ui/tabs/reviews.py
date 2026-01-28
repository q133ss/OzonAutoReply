from typing import Any, Dict

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QScrollArea, QTabWidget, QVBoxLayout, QWidget, QMessageBox, QFrame

from ...db import Database
from ..widgets.review_card import ReviewCard
from ..widgets.review_list import ReviewList


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
        self.db.update_review_status(uuid, "completed", response)
        QMessageBox.information(self, "Отправлено", "Ответ отправлен. Отзыв перемещен в завершенные.")
        self.refresh()
