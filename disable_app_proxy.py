import sqlite3
from pathlib import Path


def main() -> None:
    db_path = Path(__file__).resolve().parent / "ozon_ai.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO settings (key, value) VALUES ('proxy_enabled', '0')
            ON CONFLICT(key) DO UPDATE SET value = '0'
            """
        )
        conn.commit()

        rows = conn.execute(
            "SELECT key, value FROM settings WHERE key LIKE 'proxy_%' ORDER BY key"
        ).fetchall()
        print("Proxy settings:")
        for key, value in rows:
            if key in {"proxy_host", "proxy_username", "proxy_password"} and value:
                value = "<set>"
            print(f"{key}={value}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
