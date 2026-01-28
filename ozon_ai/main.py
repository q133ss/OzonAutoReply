import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QDialog

from .data.sample_reviews import SAMPLE_REVIEWS
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

    if db.count_reviews() == 0:
        for review in SAMPLE_REVIEWS:
            db.upsert_review(review, status="new")


def main() -> None:
    setup_logging()
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)

    base_dir = Path(__file__).resolve().parent.parent
    db_path = base_dir / "ozon_ai.sqlite"
    db = Database(str(db_path))
    db.ensure_schema()
    ensure_defaults(db)

    api_key = db.get_setting("openai_api_key")
    if not api_key:
        dialog = ApiKeyDialog()
        if dialog.exec() == QDialog.DialogCode.Accepted:
            db.set_setting("openai_api_key", dialog.key())
        else:
            sys.exit(0)

    window = MainWindow(db)
    window.show()
    app.exec()
    db.close()


if __name__ == "__main__":
    main()
