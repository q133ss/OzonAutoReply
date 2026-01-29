import logging
from datetime import datetime
from pathlib import Path

from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...db import Database
from ..dialogs import AccountSessionDialog

OZON_LOGIN_URL = (
    "https://seller.ozon.ru/app/registration/signin?"
    "redirect=L3Jldmlld3M%2FX19ycj0xJmFidF9hdHQ9MQ%3D%3D"
)


class AccountsTab(QWidget):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self._logger = logging.getLogger("ui.accounts")
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
            is_active = self._is_account_active(account["session_path"])
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, account["id"])
            widget = self._build_account_widget(account["id"], account["name"], is_active)
            item.setSizeHint(widget.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)

    def _build_account_widget(self, account_id: int, name: str, is_active: bool) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(10)

        name_label = QLabel(name)
        layout.addWidget(name_label, 1)

        status_label = QLabel("Активен" if is_active else "Не активен")
        status_label.setObjectName("StatusLabel" if is_active else "MetaText")
        layout.addWidget(status_label)

        relogin_button = QPushButton("Войти еще раз")
        relogin_button.setVisible(not is_active)
        relogin_button.clicked.connect(lambda _, acc_id=account_id: self._relogin_account(acc_id))
        layout.addWidget(relogin_button)
        return widget

    def _is_account_active(self, session_path: Optional[str]) -> bool:
        if not session_path:
            return False
        path = Path(session_path)
        if not path.exists():
            return False
        try:
            from ...ozon_reviews import _extract_company_id, _load_storage_state

            storage_state = _load_storage_state(path)
            if not storage_state:
                return False
            return _extract_company_id(storage_state) is not None
        except Exception:
            self._logger.exception("Failed to check account session")
            return False

    def _add_account(self) -> None:
        sessions_dir = Path(__file__).resolve().parents[2] / "data" / "sessions"
        dialog = AccountSessionDialog(sessions_dir, OZON_LOGIN_URL, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if not dialog.session_path:
                QMessageBox.warning(self, "Сессия не сохранена", "Не удалось сохранить сессию.")
                return
            if not Path(dialog.session_path).exists():
                QMessageBox.warning(self, "Сессия не найдена", "Файл сессии не создан. Проверьте лог.")
                return
            created_at = dialog.created_at or datetime.now().isoformat(timespec="seconds")
            self.db.add_account(dialog.account_name, dialog.session_path, created_at)
            self.refresh()

    def _relogin_account(self, account_id: int) -> None:
        sessions_dir = Path(__file__).resolve().parents[2] / "data" / "sessions"
        dialog = AccountSessionDialog(sessions_dir, OZON_LOGIN_URL, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if not dialog.session_path:
            QMessageBox.warning(self, "Сессия не сохранена", "Не удалось сохранить сессию.")
            return
        if not Path(dialog.session_path).exists():
            QMessageBox.warning(self, "Сессия не найдена", "Файл сессии не создан. Проверьте лог.")
            return
        created_at = dialog.created_at or datetime.now().isoformat(timespec="seconds")
        self.db.update_account_session(account_id, dialog.session_path, created_at)
        self.refresh()

    def _delete_account(self) -> None:
        item = self.list_widget.currentItem()
        if not item:
            QMessageBox.warning(self, "Нет выбора", "Выберите аккаунт для удаления.")
            return
        account_id = int(item.data(Qt.ItemDataRole.UserRole))
        self.db.delete_account(account_id)
        self.refresh()
