import shutil
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QDialog

from .data.sample_reviews import SAMPLE_REVIEWS
from .har_import import load_reviews_from_har
from .db import Database
from .logging_utils import setup_logging
from .ui.dialogs import ApiKeyDialog
from .ui.main_window import MainWindow
from .ui.styles import APP_STYLESHEET


def ensure_defaults(db: Database, base_dir: Path) -> None:
    if db.get_setting("min_interval") is None:
        db.set_setting("min_interval", "10")
    if db.get_setting("max_interval") is None:
        db.set_setting("max_interval", "30")

    existing_count = db.count_reviews()
    har_reviews = []
    for har_path in (base_dir / "newList.har", base_dir / "list.har"):
        har_reviews = load_reviews_from_har(har_path)
        if har_reviews:
            break
    if har_reviews and existing_count < len(har_reviews):
        for review in har_reviews:
            db.upsert_review(review, status="new")
        return
    if existing_count == 0:
        for review in SAMPLE_REVIEWS:
            db.upsert_review(review, status="new")


def main() -> None:
    setup_logging()
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET)

    base_dir = Path(__file__).resolve().parent.parent
    db_path = base_dir / "ozon_ai.db"
    legacy_db_path = base_dir / "ozon_ai.sqlite"
    if not db_path.exists() and legacy_db_path.exists():
        shutil.copy2(legacy_db_path, db_path)
    db = Database(str(db_path))
    db.ensure_schema()
    ensure_defaults(db, base_dir)

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
