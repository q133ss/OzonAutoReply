from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..real_browser_session import import_session_from_browser, open_real_browser, real_browser_profile_dir


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


class AccountSessionDialog(QDialog):
    def __init__(
        self,
        sessions_dir: Path,
        url: str,
        parent: Optional[QWidget] = None,
        proxy_config: Optional[object] = None,
        profile_dir: Optional[Path] = None,
        mode: str = "new_account",
        account_id: Optional[int] = None,
        account_name: str = "",
    ) -> None:
        super().__init__(parent)
        self.sessions_dir = sessions_dir
        self.url = url
        self.mode = mode
        self.account_id = account_id
        self.account_name = account_name.strip()
        self.session_path = ""
        self.profile_dir = str(profile_dir or real_browser_profile_dir())
        self.created_at = ""
        self._proxy_config = proxy_config
        self._browser_opened = False
        self._cdp_port = 9222

        self.setWindowTitle("Добавление аккаунта Ozon" if mode == "new_account" else "Вход в Ozon")
        self.setMinimumWidth(560)

        layout = QVBoxLayout(self)
        instructions = QLabel(self._build_instructions())
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        self.status_label = QLabel("Открываем реальный браузер...")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        button_row = QHBoxLayout()
        self.open_browser_button = QPushButton("Открыть браузер еще раз")
        self.open_browser_button.clicked.connect(self._open_browser)
        self.import_button = QPushButton("Импортировать сессию")
        self.import_button.setEnabled(False)
        self.import_button.clicked.connect(self._import_session)
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)
        button_row.addWidget(self.open_browser_button)
        button_row.addWidget(self.import_button)
        button_row.addWidget(self.cancel_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        QTimer.singleShot(0, self._open_browser)

    def _build_instructions(self) -> str:
        action = (
            "Войдите в нужный аккаунт Ozon в обычном Chrome/Edge."
            if self.mode == "new_account"
            else "Войдите заново в Ozon в обычном Chrome/Edge для выбранного аккаунта."
        )
        return (
            "Будет открыт реальный браузер без Playwright-автоматизации.\n\n"
            f"{action}\n"
            "После входа обязательно откройте страницу seller.ozon.ru/app/reviews "
            "в этом же окне, затем вернитесь сюда и нажмите \"Импортировать сессию\".\n\n"
            "Важно: этот шаг использует системные настройки браузера и Windows proxy, "
            "а не встроенный proxy приложения."
        )

    def _open_browser(self) -> None:
        try:
            browser_path, profile_dir = open_real_browser(port=self._cdp_port, start_url=self.url)
        except Exception as exc:
            self.status_label.setText("Не удалось открыть реальный браузер.")
            QMessageBox.critical(self, "Ошибка браузера", str(exc))
            return

        self._browser_opened = True
        self.profile_dir = str(profile_dir)
        self.import_button.setEnabled(True)
        self.status_label.setText(
            "Браузер открыт.\n"
            f"Путь: {browser_path}\n"
            f"Профиль: {profile_dir}\n\n"
            "Войдите в Ozon, откройте seller.ozon.ru/app/reviews и затем импортируйте сессию."
        )

    def _import_session(self) -> None:
        if not self._browser_opened:
            QMessageBox.warning(self, "Браузер не открыт", "Сначала откройте реальный браузер.")
            return
        if self.mode == "relogin" and self.account_id is None:
            QMessageBox.warning(self, "Нет аккаунта", "Не удалось определить аккаунт для повторного входа.")
            return

        account_name = self.account_name
        if self.mode == "new_account":
            default_name = account_name or f"Ozon {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            account_name, ok = QInputDialog.getText(
                self,
                "Название аккаунта",
                "Введите название аккаунта:",
                text=default_name,
            )
            account_name = (account_name or "").strip()
            if not ok or not account_name:
                return

        self.status_label.setText("Импортируем сессию из реального браузера...")
        self.import_button.setEnabled(False)
        self.open_browser_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        try:
            result = import_session_from_browser(
                account_id=self.account_id if self.mode == "relogin" else None,
                account_name=account_name,
            )
        except Exception as exc:
            self.import_button.setEnabled(True)
            self.open_browser_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
            self.status_label.setText("Не удалось импортировать сессию.")
            QMessageBox.critical(self, "Ошибка импорта", str(exc))
            return

        self.account_name = result.account_name or account_name
        self.session_path = str(result.session_path)
        self.profile_dir = str(result.profile_dir)
        self.created_at = result.created_at
        self.status_label.setText("Сессия импортирована.")

        message = (
            f"Аккаунт: {self.account_name}\n"
            f"Файл сессии: {self.session_path}\n"
            f"company_id: {result.company_id or '<missing>'}\n"
            f"needs_relogin: {result.needs_relogin}"
        )
        if result.needs_relogin or not result.company_id:
            QMessageBox.warning(
                self,
                "Сессия импортирована не полностью",
                message
                + "\n\nОткройте seller.ozon.ru/app/reviews в том же браузере и повторите импорт, "
                "если аккаунт останется неактивным.",
            )
        else:
            QMessageBox.information(self, "Готово", message)
        super().accept()
