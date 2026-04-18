from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...ai import get_openai_model, test_openai_connection
from ...db import Database
from ...proxy import ProxyConfig


class SettingsTab(QWidget):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("sk-...")

        self.test_openai_button = QPushButton("Проверить OpenAI")
        self.test_openai_button.clicked.connect(lambda: self._run_openai_test(use_proxy=True))
        self.test_openai_direct_button = QPushButton("Проверить OpenAI без прокси")
        self.test_openai_direct_button.clicked.connect(lambda: self._run_openai_test(use_proxy=False))
        openai_test_row = QWidget()
        openai_test_layout = QHBoxLayout(openai_test_row)
        openai_test_layout.setContentsMargins(0, 0, 0, 0)
        openai_test_layout.addWidget(self.test_openai_button)
        openai_test_layout.addWidget(self.test_openai_direct_button)
        openai_test_layout.addStretch(1)

        self.min_interval = QSpinBox()
        self.min_interval.setRange(1, 3600)
        self.min_interval.setSuffix(" сек")

        self.max_interval = QSpinBox()
        self.max_interval.setRange(1, 3600)
        self.max_interval.setSuffix(" сек")

        self.auto_send_enabled = QCheckBox("Включить автоотправку (только 4-5 звезд)")

        self.send_interval = QSpinBox()
        self.send_interval.setRange(0, 3600)
        self.send_interval.setSuffix(" сек")

        self.proxy_enabled = QCheckBox("Включить прокси")
        self.proxy_enabled.toggled.connect(self._update_proxy_fields)

        self.proxy_hint = QLabel(
            "Если снять галочку, прокси временно отключится, но хост, порт, логин и пароль сохранятся."
        )
        self.proxy_hint.setWordWrap(True)
        self.proxy_hint.setObjectName("MetaText")

        self.disable_proxy_button = QPushButton("Временно отключить прокси")
        self.disable_proxy_button.clicked.connect(self._temporarily_disable_proxy)

        self.proxy_type = QComboBox()
        self.proxy_type.addItem("HTTP", "http")
        self.proxy_type.addItem("HTTPS", "https")
        self.proxy_type.addItem("SOCKS5", "socks5")

        self.proxy_host = QLineEdit()
        self.proxy_host.setPlaceholderText("127.0.0.1")

        self.proxy_port = QLineEdit()
        self.proxy_port.setPlaceholderText("8080")

        self.proxy_username = QLineEdit()
        self.proxy_username.setPlaceholderText("необязательно")

        self.proxy_password = QLineEdit()
        self.proxy_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.proxy_password.setPlaceholderText("необязательно")

        proxy_toggle_row = QWidget()
        proxy_toggle_layout = QHBoxLayout(proxy_toggle_row)
        proxy_toggle_layout.setContentsMargins(0, 0, 0, 0)
        proxy_toggle_layout.addWidget(self.proxy_enabled)
        proxy_toggle_layout.addWidget(self.disable_proxy_button)
        proxy_toggle_layout.addStretch(1)

        form.addRow("OpenAI ключ:", self.api_key_input)
        form.addRow("Тест OpenAI:", openai_test_row)
        form.addRow("Минимальный интервал:", self.min_interval)
        form.addRow("Максимальный интервал:", self.max_interval)
        form.addRow("Автоотправка:", self.auto_send_enabled)
        form.addRow("Интервал отправки:", self.send_interval)
        form.addRow("Прокси:", proxy_toggle_row)
        form.addRow("", self.proxy_hint)
        form.addRow("Тип прокси:", self.proxy_type)
        form.addRow("Хост:", self.proxy_host)
        form.addRow("Порт:", self.proxy_port)
        form.addRow("Логин:", self.proxy_username)
        form.addRow("Пароль:", self.proxy_password)

        layout.addLayout(form)
        self.save_button = QPushButton("Сохранить настройки")
        self.save_button.clicked.connect(self._save)
        layout.addWidget(self.save_button)
        layout.addStretch(1)

        self._load()
        self._update_proxy_fields()

    def _load(self) -> None:
        api_key = self.db.get_setting("openai_api_key") or ""
        min_interval = int(self.db.get_setting("min_interval") or 10)
        max_interval = int(self.db.get_setting("max_interval") or 30)
        send_interval = int(self.db.get_setting("send_interval") or 5)
        auto_send_enabled = (self.db.get_setting("auto_send_enabled") or "0").lower() in {"1", "true", "yes", "on"}
        proxy_config = ProxyConfig.from_db(self.db)

        self.api_key_input.setText(api_key)
        self.min_interval.setValue(min_interval)
        self.max_interval.setValue(max_interval)
        self.send_interval.setValue(send_interval)
        self.auto_send_enabled.setChecked(auto_send_enabled)
        self.proxy_enabled.setChecked(proxy_config.enabled)

        proxy_type_index = self.proxy_type.findData(proxy_config.proxy_type)
        if proxy_type_index >= 0:
            self.proxy_type.setCurrentIndex(proxy_type_index)
        self.proxy_host.setText(proxy_config.host)
        self.proxy_port.setText(proxy_config.port)
        self.proxy_username.setText(proxy_config.username)
        self.proxy_password.setText(proxy_config.password)

    def _temporarily_disable_proxy(self) -> None:
        self.proxy_enabled.setChecked(False)

    def _update_proxy_fields(self) -> None:
        enabled = self.proxy_enabled.isChecked()
        self.disable_proxy_button.setEnabled(enabled)
        for widget in (
            self.proxy_type,
            self.proxy_host,
            self.proxy_port,
            self.proxy_username,
            self.proxy_password,
        ):
            widget.setEnabled(enabled)

    def _proxy_config_from_form(self) -> ProxyConfig:
        proxy_config = ProxyConfig(
            enabled=self.proxy_enabled.isChecked(),
            proxy_type=str(self.proxy_type.currentData() or "http"),
            host=self.proxy_host.text().strip(),
            port=self.proxy_port.text().strip(),
            username=self.proxy_username.text().strip(),
            password=self.proxy_password.text(),
        )
        proxy_config.validate()
        return proxy_config

    def _run_openai_test(self, *, use_proxy: bool) -> None:
        api_key = self.api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "Нет ключа", "Введите OpenAI ключ перед тестом.")
            return

        proxy_config = None
        if use_proxy:
            try:
                proxy_config = self._proxy_config_from_form()
            except ValueError as exc:
                QMessageBox.warning(self, "Ошибка прокси", str(exc))
                return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = test_openai_connection(
                api_key=api_key,
                model=get_openai_model(),
                timeout=30,
                proxy_config=proxy_config,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Ошибка OpenAI", str(exc))
            return
        finally:
            QApplication.restoreOverrideCursor()

        lines = [
            f"base_url: {result['base_url']}",
            f"model: {result['model']}",
            f"proxy_enabled: {result['proxy_enabled']}",
            f"proxy_server: {result['proxy_server'] or '<none>'}",
            f"ipify_ip: {result['ipify_ip'] or '<unknown>'}",
            f"status_code: {result['status_code']}",
        ]
        if result["ok"]:
            lines.append(f"reply: {result['reply']}")
            QMessageBox.information(self, "OpenAI OK", "\n".join(lines))
            return
        lines.append(f"error: {result['error'] or '<empty response>'}")
        QMessageBox.critical(self, "OpenAI error", "\n".join(lines))

    def _save(self) -> None:
        min_val = self.min_interval.value()
        max_val = self.max_interval.value()
        if min_val > max_val:
            QMessageBox.warning(self, "Ошибка", "Минимальный интервал не может быть больше максимального.")
            return

        try:
            proxy_config = self._proxy_config_from_form()
        except ValueError as exc:
            QMessageBox.warning(self, "Ошибка прокси", str(exc))
            return

        self.db.set_setting("openai_api_key", self.api_key_input.text().strip())
        self.db.set_setting("min_interval", str(min_val))
        self.db.set_setting("max_interval", str(max_val))
        self.db.set_setting("auto_send_enabled", "1" if self.auto_send_enabled.isChecked() else "0")
        self.db.set_setting("send_interval", str(self.send_interval.value()))
        self.db.set_setting("proxy_enabled", "1" if proxy_config.enabled else "0")
        self.db.set_setting("proxy_type", proxy_config.proxy_type)
        self.db.set_setting("proxy_host", proxy_config.host)
        self.db.set_setting("proxy_port", proxy_config.port)
        self.db.set_setting("proxy_username", proxy_config.username)
        self.db.set_setting("proxy_password", proxy_config.password)
        QMessageBox.information(self, "Сохранено", "Настройки сохранены.")
