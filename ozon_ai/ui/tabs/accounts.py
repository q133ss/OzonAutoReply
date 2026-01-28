from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...db import Database


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
