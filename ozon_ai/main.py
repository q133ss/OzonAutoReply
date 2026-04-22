import os
import shutil
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QDialog

from .ai import get_openai_api_key
from .com_runtime import initialize_main_thread
from .app_paths import app_root, db_path as app_db_path
from .db import Database
from .logging_utils import setup_logging
from .ui.dialogs import ApiKeyDialog
from .ui.main_window import MainWindow
from .ui.styles import APP_STYLESHEET


def ensure_defaults(db: Database) -> None:
    if db.get_setting("min_interval") is None:
        db.set_setting("min_interval", "10")
    if db.get_setting("max_interval") is None:
        db.set_setting("max_interval", "30")
    if db.get_setting("auto_send_enabled") is None:
        db.set_setting("auto_send_enabled", "0")
    if db.get_setting("send_interval") is None:
        db.set_setting("send_interval", "5")
    if db.get_setting("proxy_enabled") is None:
        db.set_setting("proxy_enabled", "0")
    if db.get_setting("proxy_type") is None:
        db.set_setting("proxy_type", "http")
    if db.get_setting("proxy_host") is None:
        db.set_setting("proxy_host", "")
    if db.get_setting("proxy_port") is None:
        db.set_setting("proxy_port", "")
    if db.get_setting("proxy_username") is None:
        db.set_setting("proxy_username", "")
    if db.get_setting("proxy_password") is None:
        db.set_setting("proxy_password", "")


    # Intentionally no review seeding; all reviews must come from the API.


def main() -> None:
    setup_logging()
    initialize_main_thread()
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)

    base_dir = app_root()
    db_path = app_db_path()
    legacy_db_path = base_dir / "ozon_ai.sqlite"
    if not db_path.exists() and legacy_db_path.exists():
        shutil.copy2(legacy_db_path, db_path)
    db = Database(str(db_path))
    db.ensure_schema()
    ensure_defaults(db)

    api_key = get_openai_api_key() or db.get_setting("openai_api_key")
    env_key = get_openai_api_key()
    if env_key and env_key != db.get_setting("openai_api_key"):
        db.set_setting("openai_api_key", env_key)
        api_key = env_key
    if api_key:
        os.environ.setdefault("OPENAI_API_KEY", api_key)
    else:
        dialog = ApiKeyDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            api_key = dialog.key()
            db.set_setting("openai_api_key", api_key)
            os.environ.setdefault("OPENAI_API_KEY", api_key)
        else:
            sys.exit(0)

    window = MainWindow(db)
    window.show()
    app.exec()
    db.close()


if __name__ == "__main__":
    main()
