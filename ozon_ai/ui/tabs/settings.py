from PyQt6.QtWidgets import (
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...db import Database


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
