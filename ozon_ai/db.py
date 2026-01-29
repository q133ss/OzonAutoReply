import sqlite3
from typing import Any, Dict, List, Optional, Set

from .ai import generate_ai_response


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row

    def close(self) -> None:
        self.conn.close()

    def ensure_schema(self) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                session_path TEXT,
                created_at TEXT
            )
            """
        )
        cur.execute("PRAGMA table_info(accounts)")
        columns = {row["name"] for row in cur.fetchall()}
        if "session_path" not in columns:
            cur.execute("ALTER TABLE accounts ADD COLUMN session_path TEXT")
        if "created_at" not in columns:
            cur.execute("ALTER TABLE accounts ADD COLUMN created_at TEXT")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                uuid TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                account_id INTEGER,
                product_title TEXT,
                product_url TEXT,
                offer_id TEXT,
                cover_image TEXT,
                sku TEXT,
                brand_id TEXT,
                brand_name TEXT,
                order_delivery_type TEXT,
                text TEXT,
                interaction_status TEXT,
                rating INTEGER,
                photos_count INTEGER,
                videos_count INTEGER,
                comments_count INTEGER,
                published_at TEXT,
                is_pinned INTEGER,
                is_quality_control INTEGER,
                chat_url TEXT,
                is_delivery_review INTEGER,
                ai_response TEXT,
                user_response TEXT
            )
            """
        )
        cur.execute("PRAGMA table_info(reviews)")
        review_columns = {row["name"] for row in cur.fetchall()}
        if "account_id" not in review_columns:
            cur.execute("ALTER TABLE reviews ADD COLUMN account_id INTEGER")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_examples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid TEXT,
                status TEXT,
                product_title TEXT,
                product_url TEXT,
                offer_id TEXT,
                cover_image TEXT,
                sku TEXT,
                brand_id TEXT,
                brand_name TEXT,
                order_delivery_type TEXT,
                text TEXT,
                interaction_status TEXT,
                rating INTEGER,
                photos_count INTEGER,
                videos_count INTEGER,
                comments_count INTEGER,
                published_at TEXT,
                is_pinned INTEGER,
                is_quality_control INTEGER,
                chat_url TEXT,
                is_delivery_review INTEGER,
                ai_response TEXT,
                user_response TEXT,
                example_response TEXT,
                created_at TEXT
            )
            """
        )
        self.conn.commit()

    def get_setting(self, key: str) -> Optional[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = cur.fetchone()
        return row[0] if row else None

    def set_setting(self, key: str, value: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        self.conn.commit()

    def list_accounts(self) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, session_path, created_at FROM accounts ORDER BY id")
        return cur.fetchall()

    def add_account(self, name: str, session_path: str, created_at: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO accounts (name, session_path, created_at) VALUES (?, ?, ?)",
            (name, session_path, created_at),
        )
        self.conn.commit()

    def delete_account(self, account_id: int) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        self.conn.commit()

    def update_account_session(self, account_id: int, session_path: str, created_at: Optional[str] = None) -> None:
        cur = self.conn.cursor()
        if created_at is None:
            cur.execute(
                "UPDATE accounts SET session_path = ? WHERE id = ?",
                (session_path, account_id),
            )
        else:
            cur.execute(
                "UPDATE accounts SET session_path = ?, created_at = ? WHERE id = ?",
                (session_path, created_at, account_id),
            )
        self.conn.commit()

    def count_reviews(self) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM reviews")
        return int(cur.fetchone()[0])

    def list_review_uuids(self) -> Set[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT uuid FROM reviews")
        return {row[0] for row in cur.fetchall()}

    def upsert_review(
        self,
        review: Dict[str, Any],
        status: str = "new",
        ai_response: Optional[str] = None,
        account_id: Optional[int] = None,
    ) -> None:
        product = review.get("product", {})
        brand = product.get("brand_info", {})
        if account_id is None:
            account_id = review.get("account_id")
        ai_response = ai_response or review.get("ai_response") or generate_ai_response(review)
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO reviews (
                uuid, status, account_id, product_title, product_url, offer_id, cover_image, sku,
                brand_id, brand_name, order_delivery_type, text, interaction_status,
                rating, photos_count, videos_count, comments_count, published_at,
                is_pinned, is_quality_control, chat_url, is_delivery_review, ai_response, user_response
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT(uuid) DO UPDATE SET
                status = CASE
                    WHEN reviews.status = 'completed' THEN reviews.status
                    ELSE excluded.status
                END,
                account_id = excluded.account_id,
                ai_response = excluded.ai_response
            """,
            (
                review.get("uuid"),
                status,
                account_id,
                product.get("title"),
                product.get("url"),
                product.get("offer_id"),
                product.get("cover_image"),
                product.get("sku"),
                brand.get("id"),
                brand.get("name"),
                review.get("orderDeliveryType"),
                review.get("text"),
                review.get("interaction_status"),
                review.get("rating"),
                review.get("photos_count"),
                review.get("videos_count"),
                review.get("comments_count"),
                review.get("published_at"),
                int(bool(review.get("is_pinned"))),
                int(bool(review.get("is_quality_control"))),
                review.get("chat_url"),
                int(bool(review.get("is_delivery_review"))),
                ai_response,
                review.get("user_response"),
            ),
        )
        self.conn.commit()

    def list_reviews(self, status: str) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT * FROM reviews WHERE status = ? ORDER BY published_at DESC
            """,
            (status,),
        )
        return [dict(row) for row in cur.fetchall()]

    def update_review_status(self, uuid: str, status: str, response: str) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            UPDATE reviews SET status = ?, user_response = ? WHERE uuid = ?
            """,
            (status, response, uuid),
        )
        self.conn.commit()

    def get_review(self, uuid: str) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM reviews WHERE uuid = ?", (uuid,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_account(self, account_id: int) -> Optional[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, name, session_path, created_at FROM accounts WHERE id = ?", (account_id,))
        return cur.fetchone()

    def list_examples(self) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM ai_examples ORDER BY id DESC")
        return [dict(row) for row in cur.fetchall()]

    def list_examples_for_rating(self, rating: int, limit: int = 3) -> List[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute(
            "SELECT * FROM ai_examples WHERE rating = ? ORDER BY id DESC LIMIT ?",
            (rating, limit),
        )
        return [dict(row) for row in cur.fetchall()]

    def save_example(self, data: Dict[str, Any], example_id: Optional[int] = None) -> int:
        fields = [
            "uuid",
            "status",
            "product_title",
            "product_url",
            "offer_id",
            "cover_image",
            "sku",
            "brand_id",
            "brand_name",
            "order_delivery_type",
            "text",
            "interaction_status",
            "rating",
            "photos_count",
            "videos_count",
            "comments_count",
            "published_at",
            "is_pinned",
            "is_quality_control",
            "chat_url",
            "is_delivery_review",
            "ai_response",
            "user_response",
            "example_response",
            "created_at",
        ]
        values = [data.get(field) for field in fields]
        cur = self.conn.cursor()
        if example_id is None:
            placeholders = ", ".join("?" for _ in fields)
            cur.execute(
                f"INSERT INTO ai_examples ({', '.join(fields)}) VALUES ({placeholders})",
                values,
            )
            self.conn.commit()
            return int(cur.lastrowid)
        cur.execute(
            f"UPDATE ai_examples SET {', '.join(f'{field} = ?' for field in fields)} WHERE id = ?",
            values + [example_id],
        )
        self.conn.commit()
        return example_id

    def delete_example(self, example_id: int) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM ai_examples WHERE id = ?", (example_id,))
        self.conn.commit()
