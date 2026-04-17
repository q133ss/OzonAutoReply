import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from PyQt6.QtCore import QProcess, QTimer
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

from ..logging_utils import get_log_path
from ..proxy import ProxyConfig


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
        proxy_config: Optional[ProxyConfig] = None,
        profile_dir: Optional[Path] = None,
        mode: str = "new_account",
    ) -> None:
        super().__init__(parent)
        self.sessions_dir = sessions_dir
        self.url = url
        self.proxy_config = proxy_config
        self.mode = mode
        self.account_name = ""
        self.session_path = ""
        self.profile_dir = ""
        self.created_at = ""
        self._session_saved = False
        self._closing = False
        self._logger = logging.getLogger("playwright.dialog")

        self._run_id = uuid4().hex
        self._control_path = self.sessions_dir / f"session_{self._run_id}.cmd"
        self._status_path = self.sessions_dir / f"session_{self._run_id}.status"
        self._error_path = self._status_path.with_suffix(".error")
        self._proxy_config_path = self.sessions_dir / f"session_{self._run_id}.proxy.json"
        self._browser_profiles_dir = self.sessions_dir.parent / "browser_profiles"
        self._browser_profiles_dir.mkdir(parents=True, exist_ok=True)
        if profile_dir is None:
            self._profile_dir = self._browser_profiles_dir / f"profile_{self._run_id}"
            self._temporary_profile = True
        else:
            self._profile_dir = Path(profile_dir)
            self._temporary_profile = False
        self.profile_dir = str(self._profile_dir)

        self.setWindowTitle("Добавление аккаунта Ozon")
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        instructions = QLabel(
            "Откроется окно браузера с постоянным профилем. Войдите в аккаунт Ozon вручную, "
            "вернитесь сюда и нажмите \"Сохранить сессию\"."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        self.status_label = QLabel("Запуск браузера...")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        button_row = QHBoxLayout()
        self.save_button = QPushButton("Сохранить сессию")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._save_session)
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)
        button_row.addWidget(self.save_button)
        button_row.addWidget(self.cancel_button)
        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._process.errorOccurred.connect(self._on_process_error)
        self._process.finished.connect(self._on_process_finished)
        self._process.readyReadStandardOutput.connect(self._on_process_output)

        self._status_timer = QTimer(self)
        self._status_timer.setInterval(300)
        self._status_timer.timeout.connect(self._poll_status)
        self._status_timer.start()

        self._start_runner()

    def _on_started(self) -> None:
        self.status_label.setText(
            "Браузер открыт с постоянным профилем. Войдите в Ozon и нажмите \"Сохранить сессию\"."
        )
        self.save_button.setEnabled(True)

    def _save_session(self) -> None:
        default_name = f"Ozon {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        name, ok = QInputDialog.getText(
            self,
            "Название аккаунта",
            "Введите название аккаунта:",
            text=default_name,
        )
        name = (name or "").strip()
        if not ok or not name:
            return

        self.account_name = name
        self.created_at = datetime.now().isoformat(timespec="seconds")
        filename = f"ozon_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid4().hex}.json"
        self.session_path = str(self.sessions_dir / filename)
        self.status_label.setText("Сохраняем сессию и профиль...")
        self.save_button.setEnabled(False)
        self._write_command({"action": "save", "session_path": self.session_path})

    def _on_session_saved(self, path: str) -> None:
        self.session_path = path
        self._session_saved = True
        self.status_label.setText(
            "Сессия сохранена. Этот профиль будет переиспользован при следующем входе."
        )
        self.save_button.setEnabled(False)
        self.cancel_button.setText("Готово")
        self.cancel_button.clicked.disconnect()
        self.cancel_button.clicked.connect(self._finish_after_save)

    def _on_error(self, message: str) -> None:
        self.status_label.setText("Не удалось сохранить сессию.")
        log_path = get_log_path()
        details = message
        if log_path:
            details = f"{message}\n\nЛог: {log_path}"
        QMessageBox.critical(self, "Ошибка Playwright", details)
        self.save_button.setEnabled(False)
        self.cancel_button.setEnabled(True)

    def _finish_after_save(self) -> None:
        if self._process.state() != QProcess.ProcessState.NotRunning:
            self.status_label.setText("Закрываем браузер...")
            self.cancel_button.setEnabled(False)
            self._write_command({"action": "stop"})
            return
        super().accept()

    def reject(self) -> None:
        if self._process.state() != QProcess.ProcessState.NotRunning:
            self._closing = True
            self.status_label.setText("Закрываем браузер...")
            self.save_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
            self._write_command({"action": "stop"})
            return
        self._cleanup_temporary_profile()
        super().reject()

    def _start_runner(self) -> None:
        log_path = get_log_path()
        self._profile_dir.mkdir(parents=True, exist_ok=True)
        if getattr(sys, "frozen", False):
            args = [
                "--run-playwright-runner",
                "--url",
                self.url,
                "--mode",
                self.mode,
                "--profile-dir",
                str(self._profile_dir),
                "--control-path",
                str(self._control_path),
                "--status-path",
                str(self._status_path),
            ]
            workdir = Path(sys.executable).resolve().parent
        else:
            args = [
                "-m",
                "ozon_ai.playwright_runner",
                "--url",
                self.url,
                "--mode",
                self.mode,
                "--profile-dir",
                str(self._profile_dir),
                "--control-path",
                str(self._control_path),
                "--status-path",
                str(self._status_path),
            ]
            workdir = Path(__file__).resolve().parents[2]
        if log_path:
            args.extend(["--log-path", str(log_path)])
        if self.proxy_config and self.proxy_config.enabled:
            try:
                self.proxy_config.validate()
                self._proxy_config_path.write_text(
                    json.dumps(self.proxy_config.to_dict(), ensure_ascii=False),
                    encoding="utf-8",
                )
                args.extend(["--proxy-config", str(self._proxy_config_path)])
            except Exception as exc:
                self._logger.exception("Invalid proxy config")
                self._on_error(str(exc))
                return
        self._logger.info(
            "Starting Playwright runner. mode=%s profile=%s proxy=%s",
            self.mode,
            self._profile_dir,
            bool(self.proxy_config and self.proxy_config.enabled),
        )
        self._process.setWorkingDirectory(str(workdir))
        self._process.start(sys.executable, args)
        if not self._process.waitForStarted(5000):
            self._on_error("Не удалось запустить встроенный Playwright браузер.")

    def _cleanup_proxy_config(self) -> None:
        try:
            self._proxy_config_path.unlink(missing_ok=True)
        except Exception:
            self._logger.exception("Failed to remove proxy config")

    def _cleanup_temporary_profile(self) -> None:
        if not self._temporary_profile or self._session_saved:
            return
        try:
            shutil.rmtree(self._profile_dir, ignore_errors=True)
        except Exception:
            self._logger.exception("Failed to remove temporary profile dir")

    def _write_command(self, payload: dict) -> None:
        try:
            self._control_path.write_text(json.dumps(payload), encoding="utf-8")
        except Exception:
            self._logger.exception("Failed to write control command")
            self._on_error("Не удалось отправить команду Playwright.")

    def _poll_status(self) -> None:
        if not self._status_path.exists():
            return
        try:
            content = self._status_path.read_text(encoding="utf-8").strip()
        except Exception:
            self._logger.exception("Failed to read status file")
            return
        if content == "ready":
            self._status_path.unlink(missing_ok=True)
            self._on_started()
            return
        if content.startswith("saved|"):
            self._status_path.unlink(missing_ok=True)
            path = content.split("|", 1)[1]
            self._on_session_saved(path)
            return
        if content in {"closed", "stopped"}:
            self._status_path.unlink(missing_ok=True)
            if not self._session_saved:
                self._on_error("Браузер закрыт до сохранения сессии.")
            return
        if content == "error":
            self._status_path.unlink(missing_ok=True)
            self._show_runner_error()

    def _show_runner_error(self) -> None:
        details = "Playwright завершился с ошибкой."
        if self._error_path.exists():
            try:
                error_text = self._error_path.read_text(encoding="utf-8")
                details = f"{details}\n\n{error_text}"
            except Exception:
                self._logger.exception("Failed to read runner error file")
        self._on_error(details)

    def _on_process_error(self, error: QProcess.ProcessError) -> None:
        self._logger.error("Playwright runner error: %s", error)
        self._on_error("Playwright процесс завершился с ошибкой.")

    def _on_process_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        self._cleanup_proxy_config()
        self._logger.info("Playwright runner finished. code=%s status=%s", exit_code, exit_status)
        if self._session_saved:
            if self.cancel_button.text() != "Готово":
                self.cancel_button.setText("Готово")
                self.cancel_button.clicked.disconnect()
                self.cancel_button.clicked.connect(self._finish_after_save)
            return
        if self._closing:
            self._cleanup_temporary_profile()
            super().reject()
            return
        self._cleanup_temporary_profile()
        self._on_error("Playwright процесс завершился неожиданно.")

    def _on_process_output(self) -> None:
        data = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="ignore")
        if data:
            self._logger.info("runner: %s", data.strip())
