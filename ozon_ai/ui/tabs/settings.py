from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

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

        self.proxy_enabled = QCheckBox("Использовать прокси")
        self.proxy_enabled.toggled.connect(self._update_proxy_fields)

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

        form.addRow("OpenAI ключ:", self.api_key_input)
        form.addRow("Минимальный интервал:", self.min_interval)
        form.addRow("Максимальный интервал:", self.max_interval)
        form.addRow("Автоотправка:", self.auto_send_enabled)
        form.addRow("Интервал отправки:", self.send_interval)
        form.addRow("Прокси:", self.proxy_enabled)
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
        self.api_key_input.setText(api_key)
        min_interval = int(self.db.get_setting("min_interval") or 10)
        max_interval = int(self.db.get_setting("max_interval") or 30)
        send_interval = int(self.db.get_setting("send_interval") or 5)
        auto_send_enabled = (self.db.get_setting("auto_send_enabled") or "0").lower() in {"1", "true", "yes", "on"}
        proxy_config = ProxyConfig.from_db(self.db)

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

    def _update_proxy_fields(self) -> None:
        enabled = self.proxy_enabled.isChecked()
        for widget in (
            self.proxy_type,
            self.proxy_host,
            self.proxy_port,
            self.proxy_username,
            self.proxy_password,
        ):
            widget.setEnabled(enabled)

    def _save(self) -> None:
        min_val = self.min_interval.value()
        max_val = self.max_interval.value()
        if min_val > max_val:
            QMessageBox.warning(self, "Ошибка", "Минимальный интервал не может быть больше максимального.")
            return

        proxy_config = ProxyConfig(
            enabled=self.proxy_enabled.isChecked(),
            proxy_type=str(self.proxy_type.currentData() or "http"),
            host=self.proxy_host.text().strip(),
            port=self.proxy_port.text().strip(),
            username=self.proxy_username.text().strip(),
            password=self.proxy_password.text(),
        )
        try:
            proxy_config.validate()
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
