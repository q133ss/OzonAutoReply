import logging
import threading
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .ai import generate_ai_response, get_openai_api_key
from .db import Database
from .ozon_reviews import fetch_all_new_reviews


class ReviewsPoller(QObject):
    synced = pyqtSignal(int)

    def __init__(self, db_path: Path, interval_ms: int = 60_000, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._db_path = Path(db_path)
        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self.poll)
        self._lock = threading.Lock()
        self._inflight = False
        self._logger = logging.getLogger("reviews.poller")

    def start(self, immediate: bool = True) -> None:
        self._timer.start()
        if immediate:
            self.poll()

    def poll(self) -> None:
        with self._lock:
            if self._inflight:
                return
            self._inflight = True
        threading.Thread(target=self._run_sync, daemon=True).start()

    def _run_sync(self) -> None:
        new_count = 0
        try:
            new_count = sync_new_reviews(self._db_path)
        except Exception:
            self._logger.exception("Failed to sync reviews")
        finally:
            with self._lock:
                self._inflight = False
        self.synced.emit(new_count)


def sync_new_reviews(db_path: Path) -> int:
    if not db_path.exists():
        return 0

    db = Database(str(db_path))
    try:
        api_key = get_openai_api_key() or db.get_setting("openai_api_key")
        min_interval = int(db.get_setting("min_interval") or 10)
        max_interval = int(db.get_setting("max_interval") or 30)
        if max_interval < min_interval:
            max_interval = min_interval
        accounts = db.list_accounts()
        if not accounts:
            return 0
        known_uuids = db.list_review_uuids()
        new_count = 0
        for account in accounts:
            session_path = account["session_path"]
            if not session_path:
                continue
            session_file = Path(session_path)
            if not session_file.exists():
                continue
            reviews = fetch_all_new_reviews(session_file)
            for review in reviews:
                uuid = review.get("uuid")
                if not uuid or uuid in known_uuids:
                    continue
                ai_response = review.get("ai_response")
                if not ai_response:
                    ai_response = generate_ai_response(
                        review,
                        api_key=api_key,
                        min_interval=min_interval,
                        max_interval=max_interval,
                    )
                db.upsert_review(review, status="new", ai_response=ai_response)
                known_uuids.add(uuid)
                new_count += 1
        return new_count
    finally:
        db.close()
