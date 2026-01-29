from datetime import datetime
from typing import Any, Dict, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QLineEdit,
)

from ...db import Database


class ExamplesTab(QWidget):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self._current_id: Optional[int] = None
        self._inputs: Dict[str, Any] = {}
        self._default_rating = 1

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        form_container = QWidget()
        form_layout = QVBoxLayout(form_container)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(10)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        self._add_line(form, "Название товара", "product_title")
        self._add_spin(form, "Рейтинг", "rating", 1, 5)
        self._add_text(form, "Текст отзыва", "text", min_height=120)
        self._add_text(form, "Пример ответа", "example_response", min_height=120)

        form_layout.addLayout(form)

        button_row = QHBoxLayout()
        self.save_button = QPushButton("Сохранить пример")
        self.save_button.clicked.connect(self._save)
        self.new_button = QPushButton("Новый")
        self.new_button.clicked.connect(self._clear_form)
        self.delete_button = QPushButton("Удалить")
        self.delete_button.clicked.connect(self._delete)
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.new_button)
        button_row.addWidget(self.delete_button)
        button_row.addStretch(1)
        form_layout.addLayout(button_row)
        form_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(form_container)

        list_container = QWidget()
        list_layout = QVBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(6)
        list_layout.addWidget(QLabel("Примеры"))
        self.examples_list = QListWidget()
        self.examples_list.itemSelectionChanged.connect(self._on_select)
        list_layout.addWidget(self.examples_list)

        layout.addWidget(scroll, 2)
        layout.addWidget(list_container, 1)

        self._refresh_list()

    def _add_line(self, form: QFormLayout, label: str, key: str, placeholder: str = "") -> None:
        widget = QLineEdit()
        if placeholder:
            widget.setPlaceholderText(placeholder)
        form.addRow(label + ":", widget)
        self._inputs[key] = widget

    def _add_text(self, form: QFormLayout, label: str, key: str, min_height: int = 100) -> None:
        widget = QPlainTextEdit()
        widget.setMinimumHeight(min_height)
        form.addRow(label + ":", widget)
        self._inputs[key] = widget

    def _add_spin(self, form: QFormLayout, label: str, key: str, min_val: int, max_val: int) -> None:
        widget = QSpinBox()
        widget.setRange(min_val, max_val)
        form.addRow(label + ":", widget)
        self._inputs[key] = widget
        if key == "rating":
            widget.setValue(self._default_rating)

    def _refresh_list(self) -> None:
        self.examples_list.clear()
        for example in self.db.list_examples():
            title = example.get("product_title") or "Без названия"
            rating = example.get("rating")
            text = (example.get("text") or "").strip()
            snippet = text[:60] + ("…" if len(text) > 60 else "")
            item = QListWidgetItem(f"#{example.get('id')} • {title} • {rating or '-'}★ • {snippet}")
            item.setData(Qt.ItemDataRole.UserRole, example)
            self.examples_list.addItem(item)

    def _on_select(self) -> None:
        items = self.examples_list.selectedItems()
        if not items:
            return
        example = items[0].data(Qt.ItemDataRole.UserRole) or {}
        self._load_example(example)

    def _load_example(self, example: Dict[str, Any]) -> None:
        self._current_id = example.get("id")
        for key, widget in self._inputs.items():
            value = example.get(key)
            if isinstance(widget, QLineEdit):
                widget.setText(value or "")
            elif isinstance(widget, QPlainTextEdit):
                widget.setPlainText(value or "")
            elif isinstance(widget, QSpinBox):
                widget.setValue(int(value or 0))

    def _collect_data(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {}
        for key, widget in self._inputs.items():
            if isinstance(widget, QLineEdit):
                data[key] = widget.text().strip() or None
            elif isinstance(widget, QPlainTextEdit):
                text = widget.toPlainText().strip()
                data[key] = text or None
            elif isinstance(widget, QSpinBox):
                data[key] = widget.value()
        data["created_at"] = datetime.now().isoformat(timespec="seconds")
        return data

    def _save(self) -> None:
        data = self._collect_data()
        if not data.get("product_title"):
            QMessageBox.warning(self, "Пустое название", "Укажите название товара.")
            return
        if not data.get("text"):
            QMessageBox.warning(self, "Пустой отзыв", "Заполните текст отзыва.")
            return
        if not data.get("example_response"):
            QMessageBox.warning(self, "Пустой ответ", "Заполните пример ответа.")
            return
        example_id = self.db.save_example(data, self._current_id)
        self._current_id = example_id
        self._refresh_list()
        QMessageBox.information(self, "Сохранено", "Пример сохранен.")

    def _clear_form(self) -> None:
        self._current_id = None
        for widget in self._inputs.values():
            if isinstance(widget, QLineEdit):
                widget.clear()
            elif isinstance(widget, QPlainTextEdit):
                widget.setPlainText("")
            elif isinstance(widget, QSpinBox):
                widget.setValue(self._default_rating)

    def _delete(self) -> None:
        if self._current_id is None:
            QMessageBox.warning(self, "Удаление", "Сначала выберите пример.")
            return
        self.db.delete_example(self._current_id)
        self._current_id = None
        self._refresh_list()
        self._clear_form()
        QMessageBox.information(self, "Удалено", "Пример удален.")
